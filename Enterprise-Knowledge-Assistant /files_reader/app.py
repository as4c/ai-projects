import streamlit as st
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_postgres import PGVector
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.document_loaders import PyPDFLoader, TextLoader, JSONLoader, Docx2txtLoader
import tempfile
import json

# Load environment variables
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
COLLECTION_NAME = "document_embeddings"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None
if "conversation_chain" not in st.session_state:
    st.session_state.conversation_chain = None
if "processed_file" not in st.session_state:
    st.session_state.processed_file = None
if "data_description" not in st.session_state:
    st.session_state.data_description = ""


def get_file_preview(uploaded_file):
    """Get preview of uploaded file content."""
    try:
        if uploaded_file.name.endswith('.json'):
            content = json.loads(uploaded_file.getvalue().decode('utf-8'))
            return json.dumps(content, indent=2)[:1000]
        elif uploaded_file.name.endswith('.txt'):
            return uploaded_file.getvalue().decode('utf-8')[:1000]
        elif uploaded_file.name.endswith('.pdf'):
            return "PDF file uploaded (preview not available)"
        elif uploaded_file.name.endswith('.docx'):
            return "DOCX file uploaded (preview not available)"
    except:
        return "Unable to preview file"


def load_document(uploaded_file):
    """Load document based on file type."""
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name

    try:
        # Load based on file type
        if uploaded_file.name.endswith('.pdf'):
            loader = PyPDFLoader(tmp_file_path)
        elif uploaded_file.name.endswith('.txt'):
            loader = TextLoader(tmp_file_path)
        elif uploaded_file.name.endswith('.json'):
            loader = JSONLoader(tmp_file_path, jq_schema='.data[]', text_content=False)
        elif uploaded_file.name.endswith('.docx'):
            loader = Docx2txtLoader(tmp_file_path)
        else:
            raise ValueError("Unsupported file format. Please upload PDF, TXT, JSON, or DOCX files.")

        documents = loader.load()
        return documents
    finally:
        # Clean up temporary file
        os.unlink(tmp_file_path)


def process_document(uploaded_file):
    """Process uploaded document and create vector store."""
    with st.spinner("Processing document..."):
        # Load document
        documents = load_document(uploaded_file)

        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_documents(documents)

        # Create embeddings
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

        # Create or update vector store
        vectorstore = PGVector.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name=COLLECTION_NAME,
            connection=DATABASE_URL,
            pre_delete_collection=True  # Clear previous collection
        )

        st.session_state.vectorstore = vectorstore
        st.session_state.processed_file = uploaded_file.name

        # Create conversation chain
        llm = ChatOpenAI(
            temperature=0.7,
            model_name="gpt-3.5-turbo",
            openai_api_key=OPENAI_API_KEY
        )

        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )

        st.session_state.conversation_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
            memory=memory,
            return_source_documents=True
        )

        return True


def main():
    st.set_page_config(
        page_title="Document Chat Assistant",
        page_icon="📚",
        layout="wide"
    )

    st.title("📚 Document Chat Assistant")
    st.markdown("Upload a document and ask questions about it!")

    # Sidebar for file upload
    with st.sidebar:
        st.header("Document Upload")
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "txt", "json", "docx"],
            help="Upload a PDF, TXT, JSON, or DOCX file to analyze"
        )

        if uploaded_file is not None:
            # Show file preview
            with st.expander("📄 File Preview", expanded=False):
                preview = get_file_preview(uploaded_file)
                st.text(preview)
            
            # Data description input
            data_description = st.text_input(
                "📝 Describe your data",
                value=st.session_state.data_description,
                placeholder="e.g., Employee records with names, emails, departments...",
                help="Describe what type of data is in this file to improve search accuracy"
            )
            st.session_state.data_description = data_description
            
            if st.session_state.processed_file != uploaded_file.name:
                if st.button("Process Document", type="primary"):
                    success = process_document(uploaded_file)
                    if success:
                        st.success(f"✅ Document '{uploaded_file.name}' processed successfully!")
                        st.session_state.messages = []  # Clear chat history
            else:
                st.info(f"📄 Currently using: {uploaded_file.name}")
                if st.button("Reprocess Document"):
                    success = process_document(uploaded_file)
                    if success:
                        st.success("✅ Document reprocessed!")
                        st.session_state.messages = []

        # Display stats
        if st.session_state.vectorstore:
            st.divider()
            st.subheader("Status")
            st.write("✅ Vector store ready")
            st.write(f"📁 File: {st.session_state.processed_file}")

    # Main chat interface
    if st.session_state.conversation_chain is None:
        st.info("👈 Please upload and process a document to start chatting!")
        st.markdown("""
        ### How to use:
        1. Upload a PDF, TXT, JSON, or DOCX file using the sidebar
        2. Click 'Process Document' to create embeddings
        3. Start asking questions about your document!
        """)
    else:
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "sources" in message and message["sources"]:
                    with st.expander("📚 View Sources"):
                        for idx, source in enumerate(message["sources"], 1):
                            st.markdown(f"**Source {idx}:**")
                            st.text(source.page_content[:300] + "...")
                            st.markdown(f"*Page: {source.metadata.get('page', 'N/A')}*")
                            st.divider()

        # Chat input
        if prompt := st.chat_input("Ask a question about your document..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    # Add data description context to the question if available
                    context_prompt = prompt
                    if st.session_state.data_description:
                        context_prompt = f"Context: This document contains {st.session_state.data_description}\n\nQuestion: {prompt}"
                    
                    response = st.session_state.conversation_chain.invoke({"question": context_prompt})
                    answer = response["answer"]
                    source_documents = response.get("source_documents", [])

                    st.markdown(answer)

                    # Display sources
                    if source_documents:
                        with st.expander("📚 View Sources"):
                            for idx, source in enumerate(source_documents, 1):
                                st.markdown(f"**Source {idx}:**")
                                st.text(source.page_content[:300] + "...")
                                st.markdown(f"*Page: {source.metadata.get('page', 'N/A')}*")
                                st.divider()

                    # Add assistant message
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": source_documents
                    })


if __name__ == "__main__":
    main()