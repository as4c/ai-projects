import streamlit as st
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "google_drive"))

from main import GoogleDriveService
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
import tempfile

STATE_PREFIX = "gdrive_"

def init_state():
    keys = ["service", "authenticated", "selected_items", "current_folder"]
    for key in keys:
        if f"{STATE_PREFIX}{key}" not in st.session_state:
            st.session_state[f"{STATE_PREFIX}{key}"] = [] if key == "selected_items" else None

def process_file_content(file_name, file_content):
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_name).suffix) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name
    
    try:
        if file_name.endswith('.pdf'):
            loader = PyPDFLoader(tmp_path)
        elif file_name.endswith('.txt') or file_name.endswith('.csv'):
            loader = TextLoader(tmp_path)
        elif file_name.endswith('.docx'):
            loader = Docx2txtLoader(tmp_path)
        else:
            try:
                loader = TextLoader(tmp_path)
            except:
                return None
        return loader.load()
    except:
        return None
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def get_all_files_in_folder(service, folder_id):
    """Recursively get all files in a folder"""
    all_files = []
    items = service.list_files(folder_id)
    
    for item in items:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            # Recursively get files from subfolder
            all_files.extend(get_all_files_in_folder(service, item['id']))
        else:
            all_files.append(item)
    
    return all_files

def index_to_vectorstore(files_data):
    all_docs = []
    for file_data in files_data:
        try:
            docs = process_file_content(file_data['name'], file_data['content'])
            if docs:
                for doc in docs:
                    doc.metadata['source'] = file_data['name']
                    doc.metadata['type'] = 'document'
                all_docs.extend(docs)
        except:
            continue
    
    if not all_docs:
        return False
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(all_docs)
    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
    PGVector.from_documents(documents=chunks, embedding=embeddings, collection_name="gdrive_docs", connection=os.getenv("DATABASE_URL"), pre_delete_collection=False)
    return True

def render_connection():
    init_state()
    
    if not st.session_state[f"{STATE_PREFIX}authenticated"]:
        if st.button("Connect to Drive", type="primary", key="gd_connect"):
            try:
                drive_service = GoogleDriveService()
                drive_service.authenticate()
                st.session_state[f"{STATE_PREFIX}service"] = drive_service
                st.session_state[f"{STATE_PREFIX}authenticated"] = True
                st.success("✅ Connected!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        st.success("✅ Connected")
        
        try:
            files = st.session_state[f"{STATE_PREFIX}service"].list_files(st.session_state[f"{STATE_PREFIX}current_folder"])
            
            # Show current path
            if st.session_state[f"{STATE_PREFIX}current_folder"]:
                if st.button("⬆️ Back", key="gd_back"):
                    st.session_state[f"{STATE_PREFIX}current_folder"] = None
                    st.rerun()
            
            # Display files and folders
            for item in files[:20]:  # Show first 20 items
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    icon = "📁" if item['mimeType'] == 'application/vnd.google-apps.folder' else "📄"
                    st.text(f"{icon} {item['name']}")
                with col2:
                    if item['mimeType'] == 'application/vnd.google-apps.folder':
                        if st.button("Open", key=f"open_{item['id']}"):
                            st.session_state[f"{STATE_PREFIX}current_folder"] = item['id']
                            st.rerun()
                with col3:
                    if st.button("Select", key=f"sel_{item['id']}"):
                        if item not in st.session_state[f"{STATE_PREFIX}selected_items"]:
                            st.session_state[f"{STATE_PREFIX}selected_items"].append(item)
            
            # Show selected items
            if st.session_state[f"{STATE_PREFIX}selected_items"]:
                st.divider()
                st.write(f"✅ {len(st.session_state[f'{STATE_PREFIX}selected_items'])} items selected")
                
                if st.button("Index to Unified Chat", type="primary", key="gd_index"):
                    with st.spinner("Processing..."):
                        # Collect all files (expand folders)
                        all_files = []
                        for item in st.session_state[f"{STATE_PREFIX}selected_items"]:
                            if item['mimeType'] == 'application/vnd.google-apps.folder':
                                # Get all files in folder recursively
                                folder_files = get_all_files_in_folder(st.session_state[f"{STATE_PREFIX}service"], item['id'])
                                all_files.extend(folder_files)
                            else:
                                all_files.append(item)
                        
                        st.info(f"Processing {len(all_files)} files...")
                        
                        files_data = []
                        for file in all_files:
                            try:
                                mime_type = file['mimeType']
                                if mime_type == 'application/vnd.google-apps.document':
                                    content = st.session_state[f"{STATE_PREFIX}service"].export_google_doc(file['id'], 'text/plain')
                                    file_name = file['name'] + '.txt'
                                elif mime_type == 'application/vnd.google-apps.spreadsheet':
                                    content = st.session_state[f"{STATE_PREFIX}service"].export_google_doc(file['id'], 'text/csv')
                                    file_name = file['name'] + '.csv'
                                else:
                                    content = st.session_state[f"{STATE_PREFIX}service"].download_file(file['id'])
                                    file_name = file['name']
                                files_data.append({'name': file_name, 'content': content})
                            except:
                                continue
                        
                        if files_data and index_to_vectorstore(files_data):
                            st.session_state.connected_tools["google_drive"] = True
                            if "gdrive_docs" not in st.session_state.active_collections:
                                st.session_state.active_collections.append("gdrive_docs")
                            st.session_state[f"{STATE_PREFIX}selected_items"] = []  # Clear selection
                            st.success(f"✅ Indexed {len(files_data)} files!")
        except Exception as e:
            st.error(f"Error: {str(e)}")
        
        st.divider()
        if st.button("Disconnect", key="gd_disconnect"):
            st.session_state[f"{STATE_PREFIX}authenticated"] = False
            st.session_state[f"{STATE_PREFIX}current_folder"] = None
            st.session_state[f"{STATE_PREFIX}selected_items"] = []
            if "google_drive" in st.session_state.connected_tools:
                del st.session_state.connected_tools["google_drive"]
            st.rerun()
