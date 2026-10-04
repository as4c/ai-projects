import streamlit as st
import os
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, JSONLoader, Docx2txtLoader
import tempfile

STATE_PREFIX = "file_reader_"

def init_state():
    if f"{STATE_PREFIX}processed_file" not in st.session_state:
        st.session_state[f"{STATE_PREFIX}processed_file"] = None

def load_document(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name

    try:
        if uploaded_file.name.endswith('.pdf'):
            loader = PyPDFLoader(tmp_file_path)
            documents = loader.load()
            return documents if documents else []
        elif uploaded_file.name.endswith('.txt'):
            loader = TextLoader(tmp_file_path)
            documents = loader.load()
            return documents if documents else []
        elif uploaded_file.name.endswith('.json'):
            import json
            from langchain.schema import Document
            with open(tmp_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            documents = []

            def format_record(item):
                """Format JSON record as readable text"""
                lines = []
                if 'emp_id' in item:
                    lines.append(f"Employee ID: {item['emp_id']}")
                if 'name' in item:
                    lines.append(f"Name: {item['name']}")
                if 'designation' in item:
                    lines.append(f"Designation: {item['designation']}")
                if 'department' in item:
                    lines.append(f"Department: {item['department']}")
                if 'email' in item:
                    lines.append(f"Email: {item['email']}")
                if 'manager_id' in item:
                    lines.append(f"Manager ID: {item['manager_id']}")
                if 'location' in item:
                    lines.append(f"Location: {item['location']}")
                for k, v in item.items():
                    if k not in ['emp_id', 'name', 'designation', 'department', 'email', 'manager_id', 'location']:
                        lines.append(f"{k}: {v}")
                return "\n".join(lines)

            # Handle different JSON structures
            items = data.get('data', []) if isinstance(data, dict) else (data if isinstance(data, list) else [data])

            for item in items:
                if isinstance(item, dict):
                    text = format_record(item)
                    documents.append(Document(
                        page_content=text,
                        metadata={'source': uploaded_file.name, 'name': item.get('name', '')}
                    ))

            return documents if documents else [Document(page_content=json.dumps(data, indent=2), metadata={'source': uploaded_file.name})]
        elif uploaded_file.name.endswith('.docx'):
            loader = Docx2txtLoader(tmp_file_path)
            return loader.load()
        else:
            raise ValueError("Unsupported file format")
    finally:
        os.unlink(tmp_file_path)

def index_document(uploaded_file, description=""):
    documents = load_document(uploaded_file)
    if not documents:
        raise ValueError("No content extracted from file")
    for doc in documents:
        doc.metadata['type'] = 'document'
        doc.metadata['source'] = uploaded_file.name
        if description:
            doc.metadata['description'] = description
            # Add description to content for better search
            doc.page_content = f"[File: {uploaded_file.name} - {description}]\n\n{doc.page_content}"
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
    PGVector.from_documents(documents=chunks, embedding=embeddings, collection_name="document_embeddings", connection=os.getenv("DATABASE_URL"), pre_delete_collection=False)
    st.session_state[f"{STATE_PREFIX}processed_file"] = uploaded_file.name
    return True

def render_connection():
    init_state()

    uploaded_file = st.file_uploader("Choose file", type=["pdf", "txt", "json", "docx"], key="fr_upload")

    if uploaded_file:
        description = st.text_input("Describe this file", placeholder="e.g., Employee org chart, API documentation", key="fr_desc")

        if st.button("Index to Unified Chat", type="primary", key="fr_index"):
            with st.spinner("Indexing..."):
                try:
                    if index_document(uploaded_file, description):
                        st.session_state.connected_tools["file_reader"] = True
                        if "document_embeddings" not in st.session_state.active_collections:
                            st.session_state.active_collections.append("document_embeddings")
                        st.success(f"✅ Indexed {uploaded_file.name}!")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    if "file_reader" in st.session_state.connected_tools:
        st.info(f"✅ Active: {st.session_state[f'{STATE_PREFIX}processed_file']}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear Index", key="fr_clear"):
                try:
                    import psycopg2
                    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
                    cur = conn.cursor()
                    cur.execute("DELETE FROM langchain_pg_embedding WHERE cmetadata->>'collection_name' = 'document_embeddings'")
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("✅ Index cleared!")
                    st.session_state[f"{STATE_PREFIX}processed_file"] = None
                except Exception as e:
                    st.error(f"Error: {e}")

        with col2:
            if st.button("Disconnect", key="fr_disconnect"):
                del st.session_state.connected_tools["file_reader"]
                st.rerun()
