import streamlit as st
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_postgres import PGVector
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.schema import Document
import base64
import tempfile
import shutil
from pathlib import Path

load_dotenv()

# Initialize session state
if "github_token" not in st.session_state:
    st.session_state.github_token = None
if "selected_repo" not in st.session_state:
    st.session_state.selected_repo = None
if "repo_files" not in st.session_state:
    st.session_state.repo_files = []
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None
if "conversation" not in st.session_state:
    st.session_state.conversation = None
if "messages" not in st.session_state:
    st.session_state.messages = []

class GitHubClient:
    def __init__(self, token):
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'
    
    def get_user_repos(self):
        """Get all repos for authenticated user"""
        all_repos = []
        page = 1
        
        while True:
            response = requests.get(
                f'{self.base_url}/user/repos',
                headers=self.headers,
                params={'per_page': 100, 'page': page, 'sort': 'updated'}
            )
            
            if response.status_code != 200:
                raise Exception(f"GitHub API error: {response.status_code} - {response.text}")
            
            repos = response.json()
            
            if not isinstance(repos, list) or not repos:
                break
            
            all_repos.extend(repos)
            
            if len(repos) < 100:
                break
            
            page += 1
        
        return all_repos
    
    def get_repo_tree(self, owner, repo, branch='main'):
        """Get complete file tree of repository"""
        response = requests.get(
            f'{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1',
            headers=self.headers
        )
        
        if response.status_code == 404:
            # Try master branch
            response = requests.get(
                f'{self.base_url}/repos/{owner}/{repo}/git/trees/master?recursive=1',
                headers=self.headers
            )
        
        return response.json().get('tree', [])
    
    def get_file_content(self, owner, repo, path):
        """Get content of a specific file"""
        response = requests.get(
            f'{self.base_url}/repos/{owner}/{repo}/contents/{path}',
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('encoding') == 'base64':
                content = base64.b64decode(data['content']).decode('utf-8', errors='ignore')
                return content
        
        return None

def should_process_file(path):
    """Filter files to process"""
    # Code files
    code_extensions = ['.py', '.js', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php', '.ts', '.jsx', '.tsx', '.cs', '.swift', '.kt']
    
    # Config and schema files
    config_extensions = ['.json', '.yaml', '.yml', '.xml', '.toml', '.ini', '.env.example', '.sql', '.prisma']
    
    # Documentation
    doc_extensions = ['.md', '.txt', '.rst']
    
    # Important files
    important_files = ['README.md', 'package.json', 'requirements.txt', 'Cargo.toml', 'go.mod', 'pom.xml', 
                      'build.gradle', 'Dockerfile', 'docker-compose.yml', '.gitignore']
    
    path_lower = path.lower()
    
    # Skip directories
    skip_dirs = ['node_modules', '.git', 'dist', 'build', '__pycache__', '.venv', 'venv', 'target', 'bin', 'obj']
    if any(skip_dir in path for skip_dir in skip_dirs):
        return False
    
    # Check if important file
    filename = os.path.basename(path)
    if filename in important_files:
        return True
    
    # Check extensions
    ext = os.path.splitext(path)[1]
    return ext in code_extensions + config_extensions + doc_extensions

def create_embeddings_from_repo(repo_files, repo_name):
    """Create embeddings from repository files"""
    documents = []
    
    for file_info in repo_files:
        doc = Document(
            page_content=file_info['content'],
            metadata={
                'source': file_info['path'],
                'repo': repo_name,
                'type': file_info['type']
            }
        )
        documents.append(doc)
    
    if not documents:
        return None, None
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    
    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
    vectorstore = PGVector.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name="github_repos",
        connection=os.getenv("DATABASE_URL"),
        pre_delete_collection=False
    )
    
    llm = ChatOpenAI(temperature=0.7, model_name="gpt-4o-mini", openai_api_key=os.getenv("OPENAI_API_KEY"))
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key="answer")
    
    conversation = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
        memory=memory,
        return_source_documents=True
    )
    
    return vectorstore, conversation

def main():
    st.set_page_config(page_title="GitHub MCP", page_icon="🐙", layout="wide")
    
    st.title("🐙 GitHub MCP Server")
    st.markdown("Index and chat with GitHub repositories")
    
    # Sidebar
    with st.sidebar:
        st.header("📦 Fetch Repository")
        
        fetch_method = st.radio("Method", ["By Token", "By URL"], horizontal=True)
        
        if fetch_method == "By Token":
            st.info("💡 Get token: GitHub Settings → Developer settings → Personal access tokens → Generate (select 'repo' scope)")
            
            env_token = os.getenv("GITHUB_TOKEN", "")
            use_env = st.checkbox("Use .env token", value=bool(env_token))
            
            if use_env and env_token:
                github_token = env_token
                st.success("✓ Using .env token")
            else:
                github_token = st.text_input("GitHub Token", type="password", placeholder="ghp_...")
            
            if st.button("Fetch My Repos") and github_token:
                try:
                    client = GitHubClient(github_token)
                    repos = client.get_user_repos()
                    st.session_state.github_client = client
                    st.session_state.repos = repos
                    st.success(f"✅ Found {len(repos)} repos")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            
            if hasattr(st.session_state, 'repos') and st.session_state.repos:
                repo_names = [f"{r.get('owner', {}).get('login', 'unknown')}/{r.get('name', 'unknown')}" for r in st.session_state.repos if isinstance(r, dict)]
                selected_repo_name = st.selectbox("Select Repository", repo_names)
            else:
                selected_repo_name = None
        
        else:  # By URL
            st.info("💡 Works with public repos, no token needed")
            repo_url = st.text_input("Repository URL", placeholder="https://github.com/owner/repo")
            
            if repo_url:
                parts = repo_url.rstrip('/').split('/')
                if len(parts) >= 2:
                    selected_repo_name = f"{parts[-2]}/{parts[-1]}"
                else:
                    st.error("Invalid URL format")
                    selected_repo_name = None
            else:
                selected_repo_name = None
        
        if selected_repo_name:
            owner, repo = selected_repo_name.split('/')
            
            if st.button("📥 Index Repository", type="primary"):
                with st.spinner(f"Indexing {selected_repo_name}..."):
                    try:
                        # Use existing client or create anonymous one
                        if hasattr(st.session_state, 'github_client'):
                            client = st.session_state.github_client
                        else:
                            client = GitHubClient("")  # Anonymous for public repos
                        tree = client.get_repo_tree(owner, repo)
                        
                        # Filter and fetch files
                        files_to_process = [f for f in tree if f['type'] == 'blob' and should_process_file(f['path'])]
                        
                        st.info(f"Processing {len(files_to_process)} files...")
                        
                        repo_files = []
                        progress_bar = st.progress(0)
                        
                        for idx, file_info in enumerate(files_to_process):
                            content = client.get_file_content(owner, repo, file_info['path'])
                            
                            if content:
                                file_type = 'code'
                                if file_info['path'].endswith('.sql'):
                                    file_type = 'schema'
                                elif file_info['path'].endswith('.md'):
                                    file_type = 'documentation'
                                elif 'model' in file_info['path'].lower() or 'schema' in file_info['path'].lower():
                                    file_type = 'schema'
                                
                                repo_files.append({
                                    'path': file_info['path'],
                                    'content': content,
                                    'type': file_type
                                })
                            
                            progress_bar.progress((idx + 1) / len(files_to_process))
                        
                        st.session_state.repo_files = repo_files
                        st.session_state.selected_repo = selected_repo_name
                        
                        # Create embeddings
                        with st.spinner("Creating embeddings..."):
                            vectorstore, conversation = create_embeddings_from_repo(repo_files, selected_repo_name)
                            
                            if vectorstore and conversation:
                                st.session_state.vectorstore = vectorstore
                                st.session_state.conversation = conversation
                                st.session_state.messages = []
                                st.success(f"✅ Indexed {len(repo_files)} files!")
                    
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        if st.session_state.selected_repo:
            st.divider()
            st.info(f"📦 Current: {st.session_state.selected_repo}")
            st.write(f"📄 {len(st.session_state.repo_files)} files indexed")
    
    # Main chat area
    st.subheader("💬 Chat with Repository")
    
    if not st.session_state.conversation:
        st.info("👈 Connect to GitHub and index a repository to start")
        
        st.markdown("### Example Queries:")
        st.markdown("""
        - Give me an overview of this project
        - What is the database schema?
        - Create an ER diagram of the tables
        - What are the main API endpoints?
        - Explain the authentication flow
        - What dependencies does this project use?
        - Show me the project structure
        """)
    else:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        if prompt := st.chat_input("Ask about the repository..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    response = st.session_state.conversation.invoke({"question": prompt})
                    answer = response["answer"]
                    
                    # Add source files
                    if response.get("source_documents"):
                        sources = set([doc.metadata['source'] for doc in response["source_documents"]])
                        answer += f"\n\n**Sources:** {', '.join(list(sources)[:5])}"
                    
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})

if __name__ == "__main__":
    main()
