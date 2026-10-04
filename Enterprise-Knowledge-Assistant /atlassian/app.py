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
from bs4 import BeautifulSoup

load_dotenv()

# Initialize session state
if "atlassian_service" not in st.session_state:
    st.session_state.atlassian_service = None
if "connected" not in st.session_state:
    st.session_state.connected = False
if "selected_items" not in st.session_state:
    st.session_state.selected_items = []
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None
if "conversation" not in st.session_state:
    st.session_state.conversation = None
if "messages" not in st.session_state:
    st.session_state.messages = []

class AtlassianClient:
    def __init__(self, base_url, email, api_token):
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(email, api_token)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({'Accept': 'application/json'})

    # CONFLUENCE
    def get_confluence_spaces(self):
        all_spaces = []
        start = 0
        limit = 100

        while True:
            response = self.session.get(
                f"{self.base_url}/wiki/rest/api/space",
                params={'limit': limit, 'start': start}
            )
            data = response.json()
            results = data.get('results', [])

            if not results:
                break

            all_spaces.extend(results)

            if len(results) < limit:
                break

            start += limit

        return all_spaces

    def get_confluence_pages(self, space_key, limit=100):
        all_pages = []
        start = 0

        while True:
            response = self.session.get(
                f"{self.base_url}/wiki/rest/api/space/{space_key}/content/page",
                params={'limit': limit, 'start': start}
            )
            data = response.json()
            results = data.get('results', [])

            if not results:
                break

            all_pages.extend(results)

            if len(results) < limit:
                break

            start += limit

        return all_pages

    def search_confluence_pages(self, query, space_key=None):
        cql = f"type=page and title~\"{query}\""
        if space_key:
            cql += f" and space={space_key}"

        response = self.session.get(
            f"{self.base_url}/wiki/rest/api/content/search",
            params={'cql': cql, 'limit': 50}
        )
        return response.json().get('results', [])

    def get_confluence_page_content(self, page_id):
        response = self.session.get(f"{self.base_url}/wiki/rest/api/content/{page_id}?expand=body.storage")
        data = response.json()
        html = data.get('body', {}).get('storage', {}).get('value', '')
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text(separator='\n', strip=True)

    # JIRA
    def get_jira_projects(self):
        response = self.session.get(f"{self.base_url}/rest/api/3/project")
        return response.json()

    def get_jira_issues(self, project_key, max_results=50):
        jql = f"project={project_key}"
        response = self.session.get(
            f"{self.base_url}/rest/api/3/search",
            params={'jql': jql, 'maxResults': max_results}
        )
        return response.json().get('issues', [])

    def get_jira_issue_details(self, issue_key):
        response = self.session.get(f"{self.base_url}/rest/api/3/issue/{issue_key}")
        data = response.json()
        fields = data.get('fields', {})
        return {
            'key': data.get('key'),
            'summary': fields.get('summary'),
            'description': fields.get('description', ''),
            'status': fields.get('status', {}).get('name'),
            'assignee': fields.get('assignee', {}).get('displayName', 'Unassigned')
        }

    # BITBUCKET
    def get_bitbucket_repos(self, workspace):
        response = self.session.get(f"{self.base_url}/2.0/repositories/{workspace}")
        return response.json().get('values', [])

    def get_bitbucket_repo_files(self, workspace, repo_slug):
        response = self.session.get(f"{self.base_url}/2.0/repositories/{workspace}/{repo_slug}/src/main/")
        return response.json().get('values', [])

def create_embeddings(items_data, collection_name):
    all_docs = []

    for item in items_data:
        doc = Document(
            page_content=item['content'],
            metadata={'source': item['title'], 'type': item['type']}
        )
        all_docs.append(doc)

    if not all_docs:
        return None, None

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(all_docs)

    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
    vectorstore = PGVector.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=collection_name,
        connection=os.getenv("DATABASE_URL"),
        pre_delete_collection=False
    )

    llm = ChatOpenAI(temperature=0.7, model_name="gpt-3.5-turbo", openai_api_key=os.getenv("OPENAI_API_KEY"))
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key="answer")

    conversation = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
        memory=memory,
        return_source_documents=True
    )

    return vectorstore, conversation

def main():
    st.set_page_config(page_title="Atlassian MCP", page_icon="🔷", layout="wide")

    st.title("🔷 Atlassian MCP Server")
    st.markdown("Connect to Jira, Confluence, or Bitbucket")

    # Sidebar
    with st.sidebar:
        st.header("🔗 Connect to Atlassian")

        service_type = st.selectbox("Select Service", ["Confluence", "Jira", "Bitbucket"])

        if not st.session_state.connected:
            # Load from .env
            env_url = os.getenv("CONFLUENCE_URL", "")
            env_email = os.getenv("CONFLUENCE_EMAIL", "")
            env_token = os.getenv("CONFLUENCE_KEY", "")

            use_env = st.checkbox("Use .env credentials", value=bool(env_url and env_email and env_token))

            if use_env and env_url and env_email and env_token:
                base_url = env_url
                email = env_email
                api_token = env_token
                st.info(f"✓ Using .env credentials\nURL: {base_url}")
            else:
                base_url = st.text_input("Atlassian URL", value=env_url, placeholder="https://yourcompany.atlassian.net")
                email = st.text_input("Email", value=env_email, placeholder="your@email.com")
                api_token = st.text_input("API Token", value=env_token, type="password")

            if st.button("Connect", type="primary"):
                if base_url and email and api_token:
                    try:
                        client = AtlassianClient(base_url, email, api_token)
                        st.session_state.atlassian_service = client
                        st.session_state.service_type = service_type
                        st.session_state.connected = True
                        st.success(f"✅ Connected to {service_type}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        else:
            st.success(f"✅ Connected to {st.session_state.service_type}")

            if st.button("Disconnect"):
                st.session_state.connected = False
                st.rerun()

            st.divider()

            # Service-specific UI
            if st.session_state.service_type == "Confluence":
                st.subheader("📚 Confluence Spaces")
                try:
                    spaces = st.session_state.atlassian_service.get_confluence_spaces()
                    space_names = {s['name']: s['key'] for s in spaces}
                    selected_space = st.selectbox("Select Space", list(space_names.keys()))

                    if selected_space:
                        space_key = space_names[selected_space]

                        # Search box
                        search_query = st.text_input("🔍 Search pages", placeholder="Type to search...")

                        if st.button("Load All Pages"):
                            with st.spinner("Loading all pages..."):
                                pages = st.session_state.atlassian_service.get_confluence_pages(space_key)
                                st.session_state.current_items = pages
                                st.success(f"Loaded {len(pages)} pages")

                        if search_query and st.button("Search"):
                            with st.spinner("Searching..."):
                                pages = st.session_state.atlassian_service.search_confluence_pages(search_query, space_key)
                                st.session_state.current_items = pages
                                st.success(f"Found {len(pages)} pages")

                        if hasattr(st.session_state, 'current_items'):
                            st.write(f"**{len(st.session_state.current_items)} pages**")

                            # Show all pages with multiselect
                            page_titles = [f"{p['title']}" for p in st.session_state.current_items]
                            selected_titles = st.multiselect("Select pages to process", page_titles)

                            if st.button("➕ Add Selected"):
                                for title in selected_titles:
                                    page = next(p for p in st.session_state.current_items if p['title'] == title)
                                    if page not in st.session_state.selected_items:
                                        st.session_state.selected_items.append(page)
                                st.success(f"Added {len(selected_titles)} pages")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

            elif st.session_state.service_type == "Jira":
                st.subheader("📋 Jira Projects")
                try:
                    projects = st.session_state.atlassian_service.get_jira_projects()
                    project_names = {p['name']: p['key'] for p in projects}
                    selected_project = st.selectbox("Select Project", list(project_names.keys()))

                    if selected_project and st.button("Load Issues"):
                        project_key = project_names[selected_project]
                        issues = st.session_state.atlassian_service.get_jira_issues(project_key)
                        st.session_state.current_items = issues
                        st.success(f"Loaded {len(issues)} issues")

                    if hasattr(st.session_state, 'current_items'):
                        for item in st.session_state.current_items[:10]:
                            if st.button(f"Select: {item['key']}", key=f"sel_{item['id']}"):
                                st.session_state.selected_items.append(item)
                except Exception as e:
                    st.error(f"Error: {str(e)}")

            elif st.session_state.service_type == "Bitbucket":
                st.subheader("🪣 Bitbucket Repos")
                workspace = st.text_input("Workspace", placeholder="your-workspace")
                if workspace and st.button("Load Repos"):
                    try:
                        repos = st.session_state.atlassian_service.get_bitbucket_repos(workspace)
                        st.session_state.current_items = repos
                        st.success(f"Loaded {len(repos)} repos")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

            if st.session_state.selected_items:
                st.divider()
                st.subheader("✅ Selected Items")
                st.write(f"{len(st.session_state.selected_items)} items")

                if st.button("📊 Process Items", type="primary"):
                    with st.spinner("Processing..."):
                        items_data = []

                        if st.session_state.service_type == "Confluence":
                            for item in st.session_state.selected_items:
                                content = st.session_state.atlassian_service.get_confluence_page_content(item['id'])
                                items_data.append({
                                    'title': item['title'],
                                    'content': content,
                                    'type': 'confluence'
                                })

                        elif st.session_state.service_type == "Jira":
                            for item in st.session_state.selected_items:
                                issue_key = item.get('key') or item.get('id')
                                details = st.session_state.atlassian_service.get_jira_issue_details(issue_key)
                                content = f"{details['summary']}\n\n{details['description']}\n\nStatus: {details['status']}\nAssignee: {details['assignee']}"
                                items_data.append({
                                    'title': issue_key,
                                    'content': content,
                                    'type': 'jira'
                                })

                        if items_data:
                            vectorstore, conversation = create_embeddings(items_data, "atlassian_docs")
                            if vectorstore and conversation:
                                st.session_state.vectorstore = vectorstore
                                st.session_state.conversation = conversation
                                st.session_state.messages = []
                                st.success("✅ Items processed!")

    # Main chat area
    st.subheader("💬 Chat with Atlassian Data")

    if not st.session_state.conversation:
        st.info("👈 Connect and process items to start chatting")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about your data..."):
        if not st.session_state.conversation:
            st.error("Please process some items first")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = st.session_state.conversation.invoke({"question": prompt})
                    answer = response["answer"]
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})

if __name__ == "__main__":
    main()
