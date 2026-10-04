import streamlit as st
import os
import requests
from requests.auth import HTTPBasicAuth
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from bs4 import BeautifulSoup

STATE_PREFIX = "atlassian_"

def init_state():
    keys = ["service", "connected", "selected_items", "service_type"]
    for key in keys:
        if f"{STATE_PREFIX}{key}" not in st.session_state:
            st.session_state[f"{STATE_PREFIX}{key}"] = [] if key == "selected_items" else None

class AtlassianClient:
    def __init__(self, base_url, email, api_token):
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(email, api_token)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({'Accept': 'application/json'})

    def get_confluence_spaces(self):
        all_spaces = []
        start = 0
        while True:
            response = self.session.get(f"{self.base_url}/wiki/rest/api/space", params={'limit': 100, 'start': start})
            data = response.json()
            results = data.get('results', [])
            if not results:
                break
            all_spaces.extend(results)
            if len(results) < 100:
                break
            start += 100
        return all_spaces

    def get_confluence_pages(self, space_key):
        all_pages = []
        start = 0
        while True:
            response = self.session.get(f"{self.base_url}/wiki/rest/api/space/{space_key}/content/page", params={'limit': 100, 'start': start})
            data = response.json()
            results = data.get('results', [])
            if not results:
                break
            all_pages.extend(results)
            if len(results) < 100:
                break
            start += 100
        return all_pages

    def get_confluence_page_content(self, page_id):
        response = self.session.get(f"{self.base_url}/wiki/rest/api/content/{page_id}?expand=body.storage")
        data = response.json()
        html = data.get('body', {}).get('storage', {}).get('value', '')
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text(separator='\\n', strip=True)

    def get_jira_projects(self):
        response = self.session.get(f"{self.base_url}/rest/api/3/project")
        return response.json()

    def get_jira_issues(self, project_key):
        response = self.session.get(f"{self.base_url}/rest/api/3/search", params={'jql': f"project={project_key}", 'maxResults': 50})
        return response.json().get('issues', [])

def index_to_vectorstore(items_data):
    all_docs = []
    for item in items_data:
        if item['content'] and item['content'].strip():  # Skip empty content
            all_docs.append(Document(page_content=item['content'], metadata={'source': item['title'], 'type': item['type']}))

    if not all_docs:
        return False

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(all_docs)

    # Filter out empty chunks
    chunks = [c for c in chunks if c.page_content and c.page_content.strip()]

    if not chunks:
        return False

    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
    PGVector.from_documents(documents=chunks, embedding=embeddings, collection_name="atlassian_docs", connection=os.getenv("DATABASE_URL"), pre_delete_collection=False)
    return True

def render_connection():
    init_state()

    service_type = st.selectbox("Service", ["Confluence", "Jira"], key="atl_service")

    if not st.session_state[f"{STATE_PREFIX}connected"]:
        base_url = st.text_input("URL", os.getenv("CONFLUENCE_URL", ""), placeholder="https://yourcompany.atlassian.net", key="atl_url")
        email = st.text_input("Email", os.getenv("CONFLUENCE_EMAIL", ""), key="atl_email")
        api_token = st.text_input("API Token", os.getenv("CONFLUENCE_KEY", ""), type="password", key="atl_token")

        if st.button("Connect", type="primary", key="atl_connect"):
            if base_url and email and api_token:
                try:
                    client = AtlassianClient(base_url, email, api_token)
                    st.session_state[f"{STATE_PREFIX}service"] = client
                    st.session_state[f"{STATE_PREFIX}service_type"] = service_type
                    st.session_state[f"{STATE_PREFIX}connected"] = True
                    st.success("✅ Connected!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    else:
        st.success(f"✅ Connected to {st.session_state[f'{STATE_PREFIX}service_type']}")

        if st.session_state[f"{STATE_PREFIX}service_type"] == "Confluence":
            try:
                spaces = st.session_state[f"{STATE_PREFIX}service"].get_confluence_spaces()
                space_names = {s['name']: s['key'] for s in spaces}
                selected_space = st.selectbox("Space", list(space_names.keys()), key="atl_space")

                if selected_space and st.button("Load Pages", key="atl_load"):
                    with st.spinner("Loading..."):
                        pages = st.session_state[f"{STATE_PREFIX}service"].get_confluence_pages(space_names[selected_space])
                        st.session_state[f"{STATE_PREFIX}current_items"] = pages
                        st.success(f"Loaded {len(pages)} pages")

                if hasattr(st.session_state, f"{STATE_PREFIX}current_items"):
                    page_titles = [p['title'] for p in st.session_state[f"{STATE_PREFIX}current_items"]]
                    selected_titles = st.multiselect("Select pages", page_titles, key="atl_pages")

                    if st.button("Index to Unified Chat", type="primary", key="atl_index"):
                        with st.spinner("Indexing..."):
                            items_data = []
                            for title in selected_titles:
                                page = next(p for p in st.session_state[f"{STATE_PREFIX}current_items"] if p['title'] == title)
                                content = st.session_state[f"{STATE_PREFIX}service"].get_confluence_page_content(page['id'])
                                if content and content.strip():  # Only add non-empty content
                                    items_data.append({'title': page['title'], 'content': content, 'type': 'confluence'})

                            if items_data:
                                if index_to_vectorstore(items_data):
                                    st.session_state.connected_tools["atlassian"] = True
                                    if "atlassian_docs" not in st.session_state.active_collections:
                                        st.session_state.active_collections.append("atlassian_docs")
                                    st.success(f"✅ Indexed {len(items_data)} items!")
                                else:
                                    st.error("No valid content to index")
                            else:
                                st.error("No pages with content found")
            except Exception as e:
                st.error(f"Error: {str(e)}")

        if st.button("Disconnect", key="atl_disconnect"):
            st.session_state[f"{STATE_PREFIX}connected"] = False
            if "atlassian" in st.session_state.connected_tools:
                del st.session_state.connected_tools["atlassian"]
            st.rerun()
