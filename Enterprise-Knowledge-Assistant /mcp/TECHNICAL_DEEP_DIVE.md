# MCP System - Technical Deep Dive

## Table of Contents
1. [System Overview](#system-overview)
2. [Models & AI Components](#models--ai-components)
3. [Embedding Generation & Storage](#embedding-generation--storage)
4. [Orchestrator Logic](#orchestrator-logic)
5. [Chat Memory & Context](#chat-memory--context)
6. [Tool Selection Mechanism](#tool-selection-mechanism)
7. [Module Deep Dive](#module-deep-dive)

---

## 1. System Overview

### What is MCP?
**MCP (Multi-Context Protocol)** is a unified RAG (Retrieval-Augmented Generation) system that:
- Connects to 5 different data sources (Atlassian, GitHub, Google Drive, Slack, File uploads)
- Indexes all data into a vector database
- Provides intelligent search across all sources
- Answers questions using retrieved context + LLM

### Core Architecture
```
Data Sources → Indexing → Vector DB → Retrieval → LLM → Answer
     ↓            ↓           ↓           ↓         ↓
  5 Modules   Embeddings  PGVector   Semantic   GPT-4o
                                      Search     mini
```

---

## 2. Models & AI Components

### 2.1 Embedding Model
**Model**: `text-embedding-ada-002` (OpenAI)
- **Purpose**: Convert text to 1536-dimensional vectors
- **Usage**: 
  - Index time: Convert documents to embeddings
  - Query time: Convert user query to embedding
- **Cost**: ~$0.0001 per 1K tokens

```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

# Generate embedding for text
vector = embeddings.embed_query("What is backend architecture?")
# Returns: [0.023, -0.015, 0.042, ...] (1536 dimensions)
```

### 2.2 Chat Model
**Model**: `gpt-4o-mini` (OpenAI)
- **Purpose**: Generate natural language answers
- **Configuration**:
  - Temperature: 0.3 (more deterministic)
  - Max tokens: 1500 (response length limit)
- **Cost**: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    temperature=0.3,
    model_name="gpt-4o-mini",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    max_tokens=1500
)
```

### 2.3 Text Splitter
**Component**: `RecursiveCharacterTextSplitter` (LangChain)
- **Purpose**: Break large documents into chunks
- **Configuration**:
  - chunk_size: 1000-1500 characters
  - chunk_overlap: 200 characters (for context continuity)

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=200
)

# Example:
doc = "Very long document..."
chunks = text_splitter.split_documents([doc])
# Returns: [chunk1, chunk2, chunk3, ...]
```

---

## 3. Embedding Generation & Storage

### 3.1 How Embeddings are Generated

**Step-by-Step Process:**

```python
# 1. Fetch raw data from source
content = "Backend architecture uses microservices..."

# 2. Create LangChain Document
from langchain.schema import Document
doc = Document(
    page_content=content,
    metadata={'source': 'confluence_page', 'type': 'document'}
)

# 3. Split into chunks
chunks = text_splitter.split_documents([doc])
# Result: [
#   Document(page_content="Backend architecture uses...", metadata={...}),
#   Document(page_content="microservices pattern with...", metadata={...})
# ]

# 4. Generate embeddings for each chunk
embeddings_model = OpenAIEmbeddings(openai_api_key=API_KEY)
for chunk in chunks:
    vector = embeddings_model.embed_query(chunk.page_content)
    # vector = [0.023, -0.015, ...] (1536 numbers)
```

### 3.2 Storage in PGVector

**Database Schema:**
```sql
-- PGVector creates this automatically
CREATE TABLE langchain_pg_embedding (
    id UUID PRIMARY KEY,
    collection_id UUID,
    embedding VECTOR(1536),  -- The 1536-dimensional vector
    document TEXT,            -- Original text chunk
    cmetadata JSONB          -- Metadata (source, type, etc.)
);

-- Vector similarity index for fast search
CREATE INDEX ON langchain_pg_embedding 
USING ivfflat (embedding vector_cosine_ops);
```

**Storage Process:**
```python
from langchain_postgres import PGVector

# Store documents with embeddings
PGVector.from_documents(
    documents=chunks,                    # List of Document objects
    embedding=embeddings_model,          # Embedding function
    collection_name="github_repos",      # Separate namespace
    connection=DATABASE_URL,             # PostgreSQL connection
    pre_delete_collection=False          # Append, don't replace
)
```

**What happens internally:**
1. For each chunk, generate embedding using OpenAI API
2. Insert into PostgreSQL: `(id, collection_id, embedding_vector, text, metadata)`
3. Create vector index for fast similarity search

### 3.3 Vector Similarity Search

**How it works:**
```python
# User query: "How does backend work?"
query_embedding = embeddings_model.embed_query("How does backend work?")
# query_embedding = [0.019, -0.012, ...]

# PostgreSQL finds similar vectors using cosine similarity
# Cosine similarity = dot(A, B) / (||A|| * ||B||)
# Returns documents with highest similarity scores

results = vectorstore.similarity_search(
    query="How does backend work?",
    k=10  # Return top 10 most similar chunks
)
```

**Example similarity scores:**
- Query: "backend architecture"
- Result 1: "Backend uses microservices..." → Similarity: 0.89
- Result 2: "Frontend React components..." → Similarity: 0.42
- Result 3: "Database schema design..." → Similarity: 0.35

---

## 4. Orchestrator Logic

### 4.1 What is the Orchestrator?

The orchestrator is a **smart router** that decides which collections to search based on the user's query.

**Location**: `app.py` → `orchestrate_tools()` function

### 4.2 How It Works

```python
def orchestrate_tools(query, active_collections):
    """
    Decides which collections to search based on query keywords
    """
    query_lower = query.lower()
    selected = []
    
    # Keyword matching rules
    rules = {
        "slack_channels": ["slack", "channel", "chat", "message"],
        "github_repos": ["code", "github", "repository", "commit", "bug"],
        "atlassian_docs": ["confluence", "jira", "ticket", "documentation"],
        "gdrive_docs": ["drive", "document", "sheet", "google"],
        "document_embeddings": ["file", "upload", "pdf"]
    }
    
    # Match query to collections
    for collection, keywords in rules.items():
        if any(keyword in query_lower for keyword in keywords):
            # Verify collection exists in database
            try:
                vs = PGVector(
                    embeddings=embeddings,
                    collection_name=collection,
                    connection=DATABASE_URL
                )
                vs.similarity_search("test", k=1)  # Test query
                selected.append(collection)
            except:
                pass  # Collection doesn't exist
    
    # Fallback: search all active collections
    return selected if selected else active_collections
```

### 4.3 Examples

**Query**: "Show me Slack channels for backend"
- Matches: `slack_channels` (keyword: "slack")
- Searches: Only `slack_channels` collection
- Result: Fast, focused search

**Query**: "What features are in JIRA and how are they coded?"
- Matches: `atlassian_docs` (keyword: "jira"), `github_repos` (keyword: "coded")
- Searches: Both collections
- Result: Cross-source answer

**Query**: "Tell me about the project"
- Matches: None
- Searches: All active collections
- Result: Comprehensive search

---

## 5. Chat Memory & Context

### 5.1 How Previous Chat is Remembered

**Component**: `ConversationBufferMemory` (LangChain)

```python
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
    output_key="answer"
)
```

**Storage Structure:**
```python
# Session state stores all messages
st.session_state.messages = [
    {"role": "user", "content": "What is backend?"},
    {"role": "assistant", "content": "Backend is...", "sources": [...]},
    {"role": "user", "content": "How does it scale?"},
    {"role": "assistant", "content": "It scales by...", "sources": [...]}
]
```

### 5.2 Conversational Retrieval Chain

**Component**: `ConversationalRetrievalChain` (LangChain)

```python
from langchain.chains import ConversationalRetrievalChain

chain = ConversationalRetrievalChain.from_llm(
    llm=llm,                              # GPT-4o-mini
    retriever=vectorstore.as_retriever(), # Vector search
    memory=memory,                        # Chat history
    return_source_documents=True
)
```

**How it processes queries:**

```
Step 1: Condense Question
------------------------
User: "How does it scale?"
History: ["What is backend?", "Backend is..."]

LLM condenses: "How does backend scale?"
(Standalone question with context)

Step 2: Retrieve Documents
--------------------------
Search vector DB for: "How does backend scale?"
Returns: Top 10-15 relevant chunks

Step 3: Generate Answer
-----------------------
Prompt to LLM:
  Context: [retrieved chunks]
  History: [previous conversation]
  Question: "How does it scale?"
  
LLM generates: "Backend scales using microservices..."
```

### 5.3 Custom Prompts

**Condense Prompt** (for chat history):
```python
condense_prompt = PromptTemplate.from_template(
    "Given the following conversation and a follow up question, "
    "rephrase the follow up question to be a standalone question.\n\n"
    "Chat History:\n{chat_history}\n"
    "Follow Up Input: {question}\n"
    "Standalone question:"
)
```

**QA Prompt** (for answer generation):
```python
qa_prompt = PromptTemplate.from_template("""
You are a helpful assistant that analyzes documents from 
Confluence, GitHub, Google Drive, Slack channels, and other sources.

Context from indexed documents:
{context}

Question: {question}

INSTRUCTIONS:
- If asked about Slack channels, list the channel names with descriptions
- For simple questions: Give concise, direct answers
- For complex questions: Provide detailed explanations
- Always use information from the context provided above

Answer:
""")
```

---

## 6. Tool Selection Mechanism

### 6.1 Multi-Collection Search

**Override similarity_search method:**

```python
def create_unified_vectorstore():
    # Base vectorstore
    vectorstore = PGVector(
        embeddings=embeddings,
        collection_name=active_collections[0],
        connection=DATABASE_URL
    )
    
    # Override search to query multiple collections
    def multi_collection_search(query, k=10):
        all_docs = []
        
        # Orchestrator selects relevant collections
        collections_to_search = orchestrate_tools(query, active_collections)
        
        # Search each collection
        for collection_name in collections_to_search:
            vs = PGVector(
                embeddings=embeddings,
                collection_name=collection_name,
                connection=DATABASE_URL
            )
            docs = vs.similarity_search(query, k=5)  # 5 per collection
            all_docs.extend(docs)
        
        # Return top k overall
        return all_docs[:k]
    
    vectorstore.similarity_search = multi_collection_search
    return vectorstore
```

### 6.2 Search Strategy

**Per-collection search:**
- Each collection: k=5 documents
- Total collections: 1-5 (based on orchestrator)
- Final result: Top 10-15 documents overall

**Example:**
```
Query: "backend code and JIRA tickets"

Orchestrator selects: [github_repos, atlassian_docs]

Search github_repos → 5 docs
Search atlassian_docs → 5 docs

Total: 10 docs sent to LLM
```

---

## 7. Module Deep Dive

### 7.1 Atlassian Module

**Purpose**: Index Confluence pages and JIRA issues

**Key Components:**
```python
class AtlassianClient:
    def __init__(self, base_url, email, api_token):
        self.auth = HTTPBasicAuth(email, api_token)
    
    def get_confluence_spaces(self):
        # GET /wiki/rest/api/space
        # Returns: [{"key": "ENG", "name": "Engineering"}, ...]
    
    def get_confluence_pages(self, space_key):
        # GET /wiki/rest/api/space/{space_key}/content/page
        # Returns: [{"id": "123", "title": "Backend Guide"}, ...]
    
    def get_confluence_page_content(self, page_id):
        # GET /wiki/rest/api/content/{page_id}?expand=body.storage
        # Returns HTML, parsed with BeautifulSoup to text
```

**Indexing Process:**
1. User selects Confluence space
2. Fetch all pages in space
3. For each page: Download HTML → Parse to text → Create Document
4. Split text into chunks
5. Generate embeddings
6. Store in `atlassian_docs` collection

**Metadata stored:**
```python
{
    'source': 'Backend Architecture Guide',
    'type': 'confluence'
}
```

### 7.2 GitHub Module

**Purpose**: Index code repositories

**Key Components:**
```python
class GitHubClient:
    def __init__(self, token):
        self.headers = {'Authorization': f'token {token}'}
    
    def get_repo_tree(self, owner, repo, branch='main'):
        # GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1
        # Returns: [{"path": "src/main.py", "type": "blob"}, ...]
    
    def get_file_content(self, owner, repo, path):
        # GET /repos/{owner}/{repo}/contents/{path}
        # Returns: Base64 encoded content, decoded to text
```

**File Filtering:**
```python
def should_process_file(path):
    code_ext = ['.py', '.js', '.java', '.cpp', '.go', ...]
    config_ext = ['.json', '.yaml', '.yml', ...]
    doc_ext = ['.md', '.txt']
    
    # Skip directories
    skip_dirs = ['node_modules', '.git', 'dist', 'build']
    
    # Process code, config, and doc files
    return ext in (code_ext + config_ext + doc_ext)
```

**Indexing Process:**
1. User provides repo URL or selects from their repos
2. Fetch repository tree (all files)
3. Filter: Only code, config, and doc files
4. Download content for each file (limit: 100 files)
5. Create Document per file
6. Split and embed
7. Store in `github_repos` collection

**Metadata stored:**
```python
{
    'source': 'src/backend/api.py',
    'repo': 'company/backend-service',
    'type': 'code'
}
```

### 7.3 Google Drive Module

**Purpose**: Index Google Docs, Sheets, PDFs, etc.

**Key Components:**
```python
class GoogleDriveService:
    def authenticate(self):
        # OAuth 2.0 flow with credentials.json
    
    def list_files(self, folder_id=None):
        # List files in folder
    
    def download_file(self, file_id):
        # Download binary file
    
    def export_google_doc(self, file_id, mime_type):
        # Export Google Doc as text/plain
        # Export Google Sheet as text/csv
```

**File Processing:**
```python
def process_file_content(file_name, file_content):
    if file_name.endswith('.pdf'):
        loader = PyPDFLoader(tmp_path)
    elif file_name.endswith('.docx'):
        loader = Docx2txtLoader(tmp_path)
    elif file_name.endswith('.txt'):
        loader = TextLoader(tmp_path)
    
    return loader.load()  # Returns Document objects
```

**Indexing Process:**
1. OAuth authentication
2. User navigates folders and selects files/folders
3. Recursively expand folders to get all files
4. For each file:
   - Google Docs → Export as text
   - Google Sheets → Export as CSV
   - PDFs/DOCX → Download and parse
5. Create Documents
6. Split and embed
7. Store in `gdrive_docs` collection

### 7.4 Slack Module

**Purpose**: Index Slack channel information

**Key Components:**
```python
def fetch_slack_channels():
    # Option 1: Real Slack API
    client = WebClient(token=SLACK_BOT_TOKEN)
    result = client.conversations_list()
    
    # Option 2: Hardcoded channels (demo mode)
    channels = [
        {"name": "backend", "description": "Backend development..."},
        {"name": "frontend", "description": "Frontend development..."}
    ]
    
    return channels
```

**Semantic Search:**
```python
def find_matching_channels(query, channels):
    # Generate query embedding
    query_embedding = embeddings_model.embed_query(query)
    
    # Calculate cosine similarity with each channel
    similarities = []
    for i, channel in enumerate(channels):
        similarity = cosine_similarity(
            query_embedding, 
            channel_embeddings[i]
        )
        similarities.append((channel, similarity))
    
    # Return top 5 matches
    similarities.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in similarities[:5]]
```

**Indexing Process:**
1. Fetch channels from Slack API or use hardcoded list
2. For each channel, create rich description:
   ```
   Slack Channel: #backend
   Description: Backend development, APIs, databases
   Topic: Java, Python, Node.js
   ```
3. Generate embeddings for each channel
4. Store in `slack_channels` collection
5. Enable semantic search: "where to ask backend questions?" → #backend

### 7.5 File Reader Module

**Purpose**: Index uploaded files (PDF, JSON, DOCX, TXT)

**Key Components:**
```python
def load_document(uploaded_file):
    if uploaded_file.name.endswith('.pdf'):
        loader = PyPDFLoader(tmp_file_path)
    
    elif uploaded_file.name.endswith('.json'):
        # Custom JSON parsing for structured data
        data = json.load(f)
        
        # Format each record as readable text
        for item in data:
            text = f"""
            Employee ID: {item['emp_id']}
            Name: {item['name']}
            Designation: {item['designation']}
            Department: {item['department']}
            """
            documents.append(Document(page_content=text))
    
    elif uploaded_file.name.endswith('.docx'):
        loader = Docx2txtLoader(tmp_file_path)
    
    return documents
```

**Special Feature - File Description:**
```python
description = "Employee org chart"

# Add description to metadata AND content
doc.metadata['description'] = description
doc.page_content = f"[File: org_chart.json - {description}]\n\n{content}"

# This helps with search:
# Query: "employee hierarchy" → Matches "org chart" in description
```

**Indexing Process:**
1. User uploads file
2. User provides description (optional but recommended)
3. Detect file type and use appropriate loader
4. For JSON: Custom formatting for better readability
5. Add description to content for better search
6. Split and embed
7. Store in `document_embeddings` collection

---

## 8. Complete Query Flow Example

**User Query**: "Who is the Head of HR and what Slack channel should I use?"

### Step 1: Orchestrator
```python
query = "Who is the Head of HR and what Slack channel should I use?"
query_lower = query.lower()

# Matches:
# - "slack" → slack_channels
# - No other keywords

selected_collections = ["slack_channels"]
# But also searches document_embeddings (org chart) due to "HR"
```

### Step 2: Multi-Collection Search
```python
# Search slack_channels
slack_docs = vectorstore.similarity_search(query, k=5)
# Returns: [
#   Document(content="Slack Channel: #hr\nDescription: HR team..."),
#   Document(content="Slack Channel: #general\n...")
# ]

# Search document_embeddings (org chart)
doc_docs = vectorstore.similarity_search(query, k=5)
# Returns: [
#   Document(content="Employee ID: 12\nName: Sushma Madduru\nDesignation: Head - HR"),
#   Document(content="Employee ID: 48\nName: Aathira...")
# ]

all_docs = slack_docs + doc_docs  # Total: 10 docs
```

### Step 3: LLM Processing
```python
# Prompt sent to GPT-4o-mini:
"""
Context from indexed documents:
1. Slack Channel: #hr
   Description: HR team discussions...
   
2. Employee ID: 12
   Name: Sushma Madduru
   Designation: Head - HR
   Department: HR
   
3. Slack Channel: #general...

Question: Who is the Head of HR and what Slack channel should I use?

Answer:
"""

# LLM Response:
"""
The Head of HR is Sushma Madduru (Employee ID: 12). 
For HR-related questions, you should use the #hr Slack channel, 
which is dedicated to HR team discussions.
"""
```

### Step 4: Display Response
```
✅ Found 10 relevant documents
Types: slack_channel, document