import streamlit as st
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_postgres import PGVector
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

from modules import atlassian, github, google_drive, file_reader, slack

load_dotenv()

# Initialize unified session state
if "connected_tools" not in st.session_state:
    st.session_state.connected_tools = {}
if "unified_conversation" not in st.session_state:
    st.session_state.unified_conversation = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_collections" not in st.session_state:
    st.session_state.active_collections = []
if "token_usage" not in st.session_state:
    st.session_state.token_usage = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}

def orchestrate_tools(query, active_collections):
    """Intelligent orchestrator - decides which tools to use based on query"""
    query_lower = query.lower()
    selected = []

    rules = {
        "slack_channels": ["slack", "channel", "chat", "message", "communicate"],
        "github_repos": ["code", "github", "repository", "commit", "pull request", "bug", "implementation"],
        "atlassian_docs": ["confluence", "jira", "ticket", "documentation", "wiki", "feature", "requirement"],
        "gdrive_docs": ["drive", "document", "sheet", "presentation", "google"],
        "document_embeddings": ["file", "upload", "pdf", "employee", "emp_id", "manager", "department", "designation", "who works", "list of", "org chart", "organization"]
    }

    for collection, keywords in rules.items():
        if any(kw in query_lower for kw in keywords):
            try:
                embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
                vs = PGVector(
                    embeddings=embeddings,
                    collection_name=collection,
                    connection=os.getenv("DATABASE_URL")
                )
                vs.similarity_search("test", k=1)
                selected.append(collection)
            except:
                pass

    return selected if selected else active_collections

def create_unified_vectorstore():
    """Create a unified vectorstore that searches all collections"""
    if not st.session_state.active_collections:
        return None

    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))

    # Use first collection as base
    vectorstore = PGVector(
        embeddings=embeddings,
        collection_name=st.session_state.active_collections[0],
        connection=os.getenv("DATABASE_URL")
    )

    # Override similarity_search to search all collections
    original_search = vectorstore.similarity_search

    def multi_collection_search(query, k=10):
        all_docs = []
        collections_to_search = orchestrate_tools(query, st.session_state.active_collections)

        print(f"\n=== ORCHESTRATOR SELECTED: {collections_to_search} ===")
        for collection_name in collections_to_search:
            try:
                vs = PGVector(
                    embeddings=embeddings,
                    collection_name=collection_name,
                    connection=os.getenv("DATABASE_URL")
                )
                docs = vs.similarity_search(query, k=5)
                print(f"✓ {collection_name}: {len(docs)} docs")
                all_docs.extend(docs)
            except Exception as e:
                print(f"✗ {collection_name}: {e}")
                continue
        print(f"=== TOTAL: {len(all_docs)} ===")
        return all_docs[:k]

    vectorstore.similarity_search = multi_collection_search
    return vectorstore

def update_unified_conversation():
    """Update the unified conversation chain with all connected tools"""
    vectorstore = create_unified_vectorstore()
    if not vectorstore:
        st.session_state.unified_conversation = None
        return

    llm = ChatOpenAI(temperature=0.3, model_name="gpt-4o-mini", openai_api_key=os.getenv("OPENAI_API_KEY"), max_tokens=1500)
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key="answer")

    # Create custom prompt that encourages listing documents
    from langchain.prompts import PromptTemplate

    condense_prompt = PromptTemplate.from_template(
        "Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question.\n\nChat History:\n{chat_history}\nFollow Up Input: {question}\nStandalone question:"
    )

    qa_prompt = PromptTemplate.from_template(
        """You are a helpful assistant that analyzes documents from Confluence, GitHub, Google Drive, Slack channels, and other sources.

Context from indexed documents:
{context}

Question: {question}

INSTRUCTIONS:
- If asked about Slack channels, list the channel names with their descriptions from the context
- For simple questions (who, what is, list, show): Give concise, direct answers
- For complex questions (how, why, explain, describe): Provide detailed explanations
- Always use information from the context provided above
- Use simple language

Answer:"""
    )

    st.session_state.unified_conversation = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs={"k": 15}),
        memory=memory,
        return_source_documents=True,
        condense_question_prompt=condense_prompt,
        combine_docs_chain_kwargs={"prompt": qa_prompt}
    )

def load_persisted_state():
    """Load persisted collections from database on startup"""
    if "state_loaded" not in st.session_state:
        st.session_state.state_loaded = True

        # Check which collections exist in database
        embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
        collection_names = ["atlassian_docs", "github_repos", "gdrive_docs", "document_embeddings", "slack_channels"]

        for collection_name in collection_names:
            try:
                vs = PGVector(
                    embeddings=embeddings,
                    collection_name=collection_name,
                    connection=os.getenv("DATABASE_URL")
                )
                # Try to query - if it works, collection exists
                vs.similarity_search("test", k=1)

                # Add to active collections
                if collection_name not in st.session_state.active_collections:
                    st.session_state.active_collections.append(collection_name)

                # Mark tool as connected
                if collection_name == "atlassian_docs":
                    st.session_state.connected_tools["atlassian"] = True
                elif collection_name == "github_repos":
                    st.session_state.connected_tools["github"] = True
                elif collection_name == "gdrive_docs":
                    st.session_state.connected_tools["google_drive"] = True
                elif collection_name == "document_embeddings":
                    st.session_state.connected_tools["file_reader"] = True
                elif collection_name == "slack_channels":
                    st.session_state.connected_tools["slack"] = True
            except:
                continue

def main():
    st.set_page_config(page_title="Unified MCP Server", page_icon="🚀", layout="wide")

    # Load persisted state on first run
    load_persisted_state()

    # Sidebar for tool connections
    with st.sidebar:
        st.title("🚀 MCP Server")
        st.markdown("### Connected Tools")

        # Show connected tools status
        tools_status = {
            "atlassian": ("🔷", "Atlassian"),
            "github": ("🐙", "GitHub"),
            "google_drive": ("📁", "Google Drive"),
            "file_reader": ("📚", "File Reader"),
            "slack": ("💬", "Slack")
        }

        for tool_key, (icon, name) in tools_status.items():
            status = "✅" if tool_key in st.session_state.connected_tools else "⚪"
            st.markdown(f"{status} {icon} {name}")

        st.markdown("---")
        st.markdown("### Connect Tools")

        # Tool connection expanders
        with st.expander("🔷 Atlassian"):
            atlassian.render_connection()

        with st.expander("🐙 GitHub"):
            github.render_connection()

        with st.expander("📁 Google Drive"):
            google_drive.render_connection()

        with st.expander("📚 File Reader"):
            file_reader.render_connection()

        with st.expander("💬 Slack"):
            slack.render_connection()

        st.markdown("---")

        # Show active collections for debugging
        if st.session_state.active_collections:
            with st.expander("📊 Debug Info"):
                st.write(f"Active collections: {st.session_state.active_collections}")
                st.write(f"Connected tools: {list(st.session_state.connected_tools.keys())}")
                st.write(f"Messages in history: {len(st.session_state.messages)}")

                # Estimate token usage
                if st.session_state.messages:
                    total_chars = sum(len(msg['content']) for msg in st.session_state.messages)
                    estimated_tokens = total_chars // 4
                    st.write(f"Estimated tokens used: ~{estimated_tokens}")

        if st.button("🔄 Refresh Context", use_container_width=True):
            update_unified_conversation()
            st.success("Context refreshed!")

    # Main chat interface
    st.title("💬 Chintu !!!")

    if not st.session_state.connected_tools:
        st.info("👈 Connect tools from the sidebar to start chatting")
        st.markdown("""
        ### How it works:
        1. Connect one or more tools (Atlassian, GitHub, Google Drive, etc.)
        2. Each tool will index its data into the unified context
        3. Ask questions that span across all connected tools

        ### Example use case:
        - Connect GitHub (your repo)
        - Connect Atlassian (Confluence docs + JIRA issues)
        - Ask: "What features are planned in JIRA and how are they implemented in the codebase?"
        """)
    else:
        # Display connected tools
        st.markdown(f"**Active Tools:** {', '.join([tools_status[k][1] for k in st.session_state.connected_tools.keys()])}")
        st.markdown("---")

        # Chat messages
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        if prompt := st.chat_input("Ask about your connected tools..."):
            # Always refresh conversation to ensure latest collections
            update_unified_conversation()

            if not st.session_state.unified_conversation:
                st.error("No data available. Please connect and index tools first.")
            else:
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Searching across all connected tools..."):
                        try:
                            response = st.session_state.unified_conversation.invoke({"question": prompt})
                            answer = response["answer"]
                            sources = response.get("source_documents", [])

                            # Debug: Show what was retrieved
                            if sources:
                                st.info(f"🔍 Found {len(sources)} relevant documents")
                                source_types = [s.metadata.get('type', 'unknown') for s in sources]
                                st.caption(f"Types: {', '.join(set(source_types))}")
                            else:
                                st.warning("⚠️ No documents found in search")

                            st.markdown(answer)
                            st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})

                        except Exception as e:
                            error_msg = str(e)
                            if "rate_limit" in error_msg.lower() or "quota" in error_msg.lower():
                                st.error("⚠️ Token limit exhausted! Please check your OpenAI API quota.")
                            elif "insufficient_quota" in error_msg.lower():
                                st.error("⚠️ OpenAI API quota exceeded. Please add credits to your account.")
                            else:
                                st.error(f"Error: {error_msg}")
                            print(f"Error details: {e}")

if __name__ == "__main__":
    main()
