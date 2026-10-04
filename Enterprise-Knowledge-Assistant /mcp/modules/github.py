import streamlit as st
import os
import requests
import base64
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

STATE_PREFIX = "github_"

def init_state():
    keys = ["client", "repos"]
    for key in keys:
        if f"{STATE_PREFIX}{key}" not in st.session_state:
            st.session_state[f"{STATE_PREFIX}{key}"] = [] if key == "repos" else None

class GitHubClient:
    def __init__(self, token):
        self.token = token
        self.headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        self.base_url = 'https://api.github.com'
    
    def get_user_repos(self):
        all_repos = []
        page = 1
        while True:
            response = requests.get(f'{self.base_url}/user/repos', headers=self.headers, params={'per_page': 100, 'page': page, 'sort': 'updated'})
            if response.status_code != 200:
                raise Exception(f"GitHub API error: {response.status_code}")
            repos = response.json()
            if not isinstance(repos, list) or not repos:
                break
            all_repos.extend(repos)
            if len(repos) < 100:
                break
            page += 1
        return all_repos
    
    def get_repo_tree(self, owner, repo, branch='main'):
        response = requests.get(f'{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1', headers=self.headers)
        if response.status_code == 404:
            response = requests.get(f'{self.base_url}/repos/{owner}/{repo}/git/trees/master?recursive=1', headers=self.headers)
        return response.json().get('tree', [])
    
    def get_file_content(self, owner, repo, path):
        response = requests.get(f'{self.base_url}/repos/{owner}/{repo}/contents/{path}', headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            if data.get('encoding') == 'base64':
                return base64.b64decode(data['content']).decode('utf-8', errors='ignore')
        return None

def should_process_file(path):
    code_ext = ['.py', '.js', '.java', '.cpp', '.go', '.rs', '.rb', '.php', '.ts', '.jsx', '.tsx']
    config_ext = ['.json', '.yaml', '.yml', '.xml', '.toml']
    doc_ext = ['.md', '.txt']
    important = ['README.md', 'package.json', 'requirements.txt', 'Dockerfile']
    
    skip_dirs = ['node_modules', '.git', 'dist', 'build', '__pycache__', 'venv']
    if any(skip_dir in path for skip_dir in skip_dirs):
        return False
    
    filename = os.path.basename(path)
    if filename in important:
        return True
    
    ext = os.path.splitext(path)[1]
    return ext in code_ext + config_ext + doc_ext

def index_to_vectorstore(repo_files, repo_name):
    documents = [Document(page_content=f['content'], metadata={'source': f['path'], 'repo': repo_name, 'type': 'code'}) for f in repo_files]
    if not documents:
        return False
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
    PGVector.from_documents(documents=chunks, embedding=embeddings, collection_name="github_repos", connection=os.getenv("DATABASE_URL"), pre_delete_collection=False)
    return True

def render_connection():
    init_state()
    
    method = st.radio("Method", ["By Token", "By URL"], horizontal=True, key="gh_method")
    
    if method == "By Token":
        github_token = st.text_input("GitHub Token", os.getenv("GITHUB_TOKEN", ""), type="password", placeholder="ghp_...", key="gh_token")
        
        if st.button("Fetch Repos", key="gh_fetch") and github_token:
            try:
                client = GitHubClient(github_token)
                repos = client.get_user_repos()
                st.session_state[f"{STATE_PREFIX}client"] = client
                st.session_state[f"{STATE_PREFIX}repos"] = repos
                st.success(f"✅ Found {len(repos)} repos")
            except Exception as e:
                st.error(f"Error: {str(e)}")
        
        if st.session_state[f"{STATE_PREFIX}repos"]:
            repo_names = [f"{r.get('owner', {}).get('login', 'unknown')}/{r.get('name', 'unknown')}" for r in st.session_state[f"{STATE_PREFIX}repos"] if isinstance(r, dict)]
            selected_repo = st.selectbox("Select Repo", repo_names, key="gh_repo")
        else:
            selected_repo = None
    else:
        st.info("Works with public repos")
        repo_url = st.text_input("Repository URL", placeholder="https://github.com/owner/repo", key="gh_url")
        
        if repo_url:
            parts = repo_url.rstrip('/').split('/')
            if len(parts) >= 2:
                selected_repo = f"{parts[-2]}/{parts[-1]}"
            else:
                st.error("Invalid URL")
                selected_repo = None
        else:
            selected_repo = None
    
    if selected_repo and st.button("Index to Unified Chat", type="primary", key="gh_index"):
        owner, repo = selected_repo.split('/')
        with st.spinner(f"Indexing {selected_repo}..."):
            try:
                client_key = f"{STATE_PREFIX}client"
                if client_key in st.session_state and st.session_state[client_key] is not None:
                    client = st.session_state[client_key]
                else:
                    client = GitHubClient("")  # Anonymous for public repos
                
                tree = client.get_repo_tree(owner, repo)
                files_to_process = [f for f in tree if f['type'] == 'blob' and should_process_file(f['path'])]
                
                repo_files = []
                progress = st.progress(0)
                for idx, file_info in enumerate(files_to_process[:100]):
                    content = client.get_file_content(owner, repo, file_info['path'])
                    if content:
                        repo_files.append({'path': file_info['path'], 'content': content})
                    progress.progress((idx + 1) / min(len(files_to_process), 100))
                
                if repo_files and index_to_vectorstore(repo_files, selected_repo):
                    st.session_state.connected_tools["github"] = True
                    if "github_repos" not in st.session_state.active_collections:
                        st.session_state.active_collections.append("github_repos")
                    st.success(f"✅ Indexed {len(repo_files)} files!")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    if "github" in st.session_state.connected_tools and st.button("Disconnect", key="gh_disconnect"):
        del st.session_state.connected_tools["github"]
        st.rerun()
