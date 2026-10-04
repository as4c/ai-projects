import streamlit as st
import os
import sys
import warnings
from pathlib import Path

from main import GoogleDriveService
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_postgres import PGVector
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader, UnstructuredExcelLoader
from dotenv import load_dotenv
import tempfile

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

load_dotenv()

# Initialize session state
if "drive_service" not in st.session_state:
    st.session_state.drive_service = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_folder" not in st.session_state:
    st.session_state.current_folder = None
if "selected_files" not in st.session_state:
    st.session_state.selected_files = []
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None
if "conversation" not in st.session_state:
    st.session_state.conversation = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "vectorstore_loaded" not in st.session_state:
    st.session_state.vectorstore_loaded = False

def load_existing_vectorstore():
    """Load existing vectorstore from database."""
    # Skip auto-loading for now to avoid errors
    # User can query after processing new files
    return None, None

def process_file_content(file_name, file_content):
    """Process file and extract text."""
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
        elif file_name.endswith('.xlsx') or file_name.endswith('.xls'):
            loader = UnstructuredExcelLoader(tmp_path, mode="elements")
        else:
            # Try as text for unknown types
            try:
                loader = TextLoader(tmp_path)
            except:
                return None

        return loader.load()
    except Exception as e:
        st.warning(f"Error processing {file_name}: {str(e)}")
        return None
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def create_embeddings(files_data):
    """Create embeddings from files."""
    all_docs = []

    for file_data in files_data:
        try:
            docs = process_file_content(file_data['name'], file_data['content'])
            if docs:
                for doc in docs:
                    doc.metadata['source'] = file_data['name']
                all_docs.extend(docs)
        except Exception as e:
            st.warning(f"Skipped {file_data['name']}: {str(e)}")
            continue

    if not all_docs:
        return None, None

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(all_docs)

    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
    vectorstore = PGVector.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name="gdrive_docs",
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
    st.set_page_config(page_title="Google Drive MCP", page_icon="📁", layout="wide")

    st.title("📁 Google Drive MCP Server")

    # Load existing vectorstore on first run
    if not st.session_state.vectorstore_loaded:
        vectorstore, conversation = load_existing_vectorstore()
        if vectorstore and conversation:
            st.session_state.vectorstore = vectorstore
            st.session_state.conversation = conversation
        st.session_state.vectorstore_loaded = True

    # Sidebar
    with st.sidebar:
        st.header("🔗 Connect to Drive")

        # Load existing data button
        if not st.session_state.conversation:
            if st.button("📂 Load Existing Data"):
                with st.spinner("Loading existing data..."):
                    try:
                        embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
                        vectorstore = PGVector(
                            embeddings=embeddings,
                            collection_name="gdrive_docs",
                            connection=os.getenv("DATABASE_URL")
                        )

                        llm = ChatOpenAI(temperature=0.7, model_name="gpt-3.5-turbo", openai_api_key=os.getenv("OPENAI_API_KEY"))
                        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key="answer")

                        conversation = ConversationalRetrievalChain.from_llm(
                            llm=llm,
                            retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
                            memory=memory,
                            return_source_documents=True
                        )

                        st.session_state.vectorstore = vectorstore
                        st.session_state.conversation = conversation
                        st.success("✅ Loaded existing data!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"No existing data found: {str(e)}")

        st.divider()

        if not st.session_state.authenticated:
            if st.button("Connect to Google Drive", type="primary"):
                try:
                    drive_service = GoogleDriveService()
                    drive_service.authenticate()
                    st.session_state.drive_service = drive_service
                    st.session_state.authenticated = True
                    st.success("✅ Connected to Google Drive!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.success("✅ Connected to Google Drive")

            if st.button("Disconnect"):
                st.session_state.authenticated = False
                st.session_state.drive_service = None
                st.rerun()

            st.divider()
            st.subheader("📂 Browse Files")

            # List files
            try:
                files = st.session_state.drive_service.list_files(st.session_state.current_folder)

                for file in files:
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        icon = "📁" if file['mimeType'] == 'application/vnd.google-apps.folder' else "📄"
                        st.text(f"{icon} {file['name']}")

                    with col2:
                        if file['mimeType'] == 'application/vnd.google-apps.folder':
                            if st.button("Open", key=f"open_{file['id']}"):
                                st.session_state.current_folder = file['id']
                                st.rerun()
                        else:
                            if st.button("Select", key=f"sel_{file['id']}"):
                                if file not in st.session_state.selected_files:
                                    st.session_state.selected_files.append(file)

                if st.session_state.current_folder:
                    if st.button("⬆️ Back"):
                        st.session_state.current_folder = None
                        st.rerun()

            except Exception as e:
                st.error(f"Error: {str(e)}")

            if st.session_state.selected_files:
                st.divider()
                st.subheader("✅ Selected Files")
                for file in st.session_state.selected_files:
                    st.text(f"• {file['name']}")

                if st.button("📊 Process Files", type="primary"):
                    with st.spinner("Processing..."):
                        files_data = []
                        for file in st.session_state.selected_files:
                            try:
                                # Check if it's a Google Docs file
                                mime_type = file['mimeType']

                                if mime_type == 'application/vnd.google-apps.document':
                                    # Google Doc - export as plain text
                                    content = st.session_state.drive_service.export_google_doc(
                                        file['id'], 'text/plain'
                                    )
                                    file_name = file['name'] + '.txt'
                                elif mime_type == 'application/vnd.google-apps.spreadsheet':
                                    # Google Sheet - export as CSV
                                    content = st.session_state.drive_service.export_google_doc(
                                        file['id'], 'text/csv'
                                    )
                                    file_name = file['name'] + '.csv'
                                elif mime_type == 'application/vnd.google-apps.presentation':
                                    # Google Slides - export as plain text
                                    content = st.session_state.drive_service.export_google_doc(
                                        file['id'], 'text/plain'
                                    )
                                    file_name = file['name'] + '.txt'
                                else:
                                    # Regular file - download
                                    content = st.session_state.drive_service.download_file(file['id'])
                                    file_name = file['name']

                                files_data.append({'name': file_name, 'content': content})
                            except Exception as e:
                                st.warning(f"Skipped {file['name']}: {str(e)}")

                        if files_data:
                            vectorstore, conversation = create_embeddings(files_data)
                            if vectorstore and conversation:
                                st.session_state.vectorstore = vectorstore
                                st.session_state.conversation = conversation
                                st.session_state.messages = []
                                st.success("✅ Files processed!")
                        else:
                            st.error("No files could be processed")

    # Main area - Always show chat
    st.subheader("💬 Chat with your documents")

    # Show info if not ready
    if not st.session_state.conversation:
        st.info("💡 Upload and process files to start chatting, or query existing data if available")

    # Display messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input - always available
    if prompt := st.chat_input("Ask about your documents..."):
        if not st.session_state.conversation:
            st.error("Please process some files first or wait for existing data to load")
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
