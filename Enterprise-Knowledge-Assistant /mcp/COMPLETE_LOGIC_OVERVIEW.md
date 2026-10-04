# MCP System - Complete Logic Overview

## Quick Summary

**What MCP Does**: Unified search across 5 data sources using AI embeddings

**How It Works**: 
1. Connect to data sources (GitHub, Slack, Confluence, etc.)
2. Convert all data to vector embeddings
3. Store in PostgreSQL with pgvector
4. When user asks question → Search vectors → Get relevant docs → LLM generates answer

---

## 1. Core Concepts Explained Simply

### 1.1 What are Embeddings?

**Simple Explanation**: Embeddings convert text into numbers that capture meaning.

```
Text: "backend architecture"
Embedding: [0.023, -0.015, 0.042, ..., 0.018]  (1536 numbers)

Text: "server design"  
Embedding: [0.021, -0.013, 0.040, ..., 0.016]  (similar numbers!)

Text: "frontend styling"
Embedding: [-0.045, 0.032, -0.018, ..., -0.025]  (different numbers)
```

**Why useful?**: Similar meanings = similar numbers = easy to find related content

### 1.2 Vector Similarity Search

**How it finds relevant documents:**

```python
# User asks: "How does backend work?"
query_vector = [0.023, -0.015, 0.042, ...]

# Database has:
Doc1: "Backend uses microservices" → [0.021, -0.013, 0.040, ...]
Doc2: "Frontend uses React" → [-0.045, 0.032, -0.018, ...]
Doc3: "Database schema design" → [0.015, -0.008, 0.035, ...]

# Calculate similarity (cosine similarity):
query vs Doc1 = 0.89  ← Very similar!
query vs Doc2 = 0.32  ← Not similar
query vs Doc3 = 0.67  ← Somewhat similar

# Return: Doc1, Doc3 (most relevant)
```

### 1.3 RAG (Retrieval-Augmented Generation)

**Traditional LLM**: Only knows what it was trained on
**RAG**: LLM + Your specific data

```
User Question
     ↓
Search Vector DB → Find relevant docs
     ↓
Send docs + question to LLM
     ↓
LLM generates answer using YOUR data
```

---

## 2. System Components Explained

### 2.1 The 5 Modules (Data Connectors)

Each module does the same 3 things:
1. **Connect**: Authenticate with external service
2. **Fetch**: Download data (pages, files, code, etc.)
3. **Index**: Convert to embeddings and store

#### Module 1: Atlassian (Confluence + JIRA)
```
Connect → List Spaces → Select Space → Fetch Pages → 
Parse HTML to Text → Split into Chunks → Embed → Store
```

**Example Data Indexed:**
- Confluence page: "Backend Architecture Guide"
- JIRA ticket: "Implement user authentication"

#### Module 2: GitHub
```
Connect → List Repos → Select Repo → Get File Tree → 
Filter Code Files → Download Content → Embed → Store
```

**Example Data Indexed:**
- `src/api/auth.py` - Authentication code
- `README.md` - Project documentation
- `config.json` - Configuration

#### Module 3: Google Drive
```
OAuth Login → Browse Folders → Select Files → 
Download/Export → Parse (PDF/DOCX/Sheets) → Embed → Store
```

**Example Data Indexed:**
- "Product Requirements.pdf"
- "Q4 Roadmap.docx"
- "Employee Data.csv"

#### Module 4: Slack
```
Connect → Fetch Channels → Create Channel Descriptions → 
Embed Channel Info → Store
```

**Example Data Indexed:**
- #backend: "Backend development, APIs, databases"
- #frontend: "Frontend development, React, UI/UX"

#### Module 5: File Reader
```
Upload File → Detect Type → Parse → 
Add Description → Embed → Store
```

**Example Data Indexed:**
- org_chart.json: Employee hierarchy
- api_docs.pdf: API documentation

### 2.2 Vector Database (PGVector)

**What it stores:**

| ID | Collection | Embedding Vector | Text | Metadata |
|----|-----------|------------------|------|----------|
| 1 | github_repos | [0.02, -0.01, ...] | "def authenticate(user)..." | {source: "auth.py"} |
| 2 | atlassian_docs | [0.03, 0.02, ...] | "Backend uses microservices..." | {source: "Architecture"} |
| 3 | slack_channels | [-0.01, 0.04, ...] | "Slack Channel: #backend..." | {channel: "backend"} |

**5 Separate Collections:**
1. `atlassian_docs` - Confluence pages, JIRA tickets
2. `github_repos` - Code files, README files
3. `gdrive_docs` - Google Drive documents
4. `slack_channels` - Slack channel information
5. `document_embeddings` - Uploaded files

### 2.3 Orchestrator (Smart Router)

**Job**: Decide which collections to search based on query

**Logic:**
```python
Query: "Show me backend code"
Keywords detected: "code" → Search github_repos

Query: "What Slack channel for HR?"
Keywords detected: "slack" → Search slack_channels

Query: "Tell me about the project"
No keywords → Search ALL collections
```

**Keyword Rules:**
```python
{
    "slack_channels": ["slack", "channel", "chat"],
    "github_repos": ["code", "github", "repository", "bug"],
    "atlassian_docs": ["confluence", "jira", "ticket", "wiki"],
    "gdrive_docs": ["drive", "document", "sheet"],
    "document_embeddings": ["file", "upload", "pdf"]
}
```

### 2.4 Conversation Chain (Memory)

**How it remembers previous messages:**

```python
# Conversation stored in session:
messages = [
    {"role": "user", "content": "What is backend?"},
    {"role": "assistant", "content": "Backend is the server-side..."},
    {"role": "user", "content": "How does it scale?"},  ← Current question
]

# LLM sees full history:
# Previous: "What is backend?" → "Backend is..."
# Current: "How does it scale?"
# LLM understands "it" = "backend"
```

**ConversationalRetrievalChain** does 2 things:
1. **Condense**: Convert "How does it scale?" → "How does backend scale?"
2. **Answer**: Use condensed question to search + generate answer

---

## 3. Complete Flow: Question to Answer

### Example Query: "Who is the Head of HR?"

#### Step 1: User Input
```
User types: "Who is the Head of HR?"
```

#### Step 2: Add to Session
```python
st.session_state.messages.append({
    "role": "user", 
    "content": "Who is the Head of HR?"
})
```

#### Step 3: Orchestrator Selection
```python
query = "Who is the Head of HR?"
query_lower = "who is the head of hr?"

# Check keywords:
# "slack"? No
# "code"? No
# "confluence"? No
# "drive"? No
# "file"? No

# No match → Search ALL active collections
selected = ["atlassian_docs", "github_repos", "gdrive_docs", 
            "slack_channels", "document_embeddings"]
```

#### Step 4: Generate Query Embedding
```python
embeddings_model = OpenAIEmbeddings()
query_vector = embeddings_model.embed_query("Who is the Head of HR?")
# Result: [0.019, -0.012, 0.033, ..., 0.021]
```

#### Step 5: Search Each Collection
```python
all_docs = []

# Search document_embeddings (org_chart.json)
vs1 = PGVector(collection_name="document_embeddings")
docs1 = vs1.similarity_search(query_vector, k=5)
# Returns:
# [
#   Document("Employee ID: 12\nName: Sushma Madduru\nDesignation: Head - HR"),
#   Document("Employee ID: 48\nName: Aathira\nDesignation: HR Generalist"),
#   ...
# ]

# Search slack_channels
vs2 = PGVector(collection_name="slack_channels")
docs2 = vs2.similarity_search(query_vector, k=5)
# Returns:
# [
#   Document("Slack Channel: #hr\nDescription: HR team discussions"),
#   ...
# ]

# Search other collections (less relevant results)
# ...

all_docs = docs1 + docs2 + ...  # Total: 10-15 docs
```

#### Step 6: Rank by Similarity
```python
# PostgreSQL already ranked by cosine similarity
# Top results:
# 1. "Employee ID: 12, Name: Sushma Madduru, Designation: Head - HR" (0.91)
# 2. "Employee ID: 48, Name: Aathira, Designation: HR Generalist" (0.78)
# 3. "Slack Channel: #hr" (0.65)
```

#### Step 7: Build LLM Prompt
```python
prompt = f"""
You are a helpful assistant that analyzes documents.

Context from indexed documents:
{all_docs[0].page_content}
{all_docs[1].page_content}
{all_docs[2].page_content}
...

Question: Who is the Head of HR?

INSTRUCTIONS:
- Use information from the context above
- Give concise, direct answers

Answer:
"""
```

#### Step 8: LLM Processing
```python
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
response = llm.invoke(prompt)

# LLM reads context and generates:
answer = "The Head of HR is Sushma Madduru (Employee ID: 12)."
```

#### Step 9: Display Response
```python
st.chat_message("assistant").markdown(answer)
st.info("🔍 Found 10 relevant documents")
st.caption("Types: document, slack_channel")

# Add to session
st.session_state.messages.append({
    "role": "assistant",
    "content": answer,
    "sources": all_docs
})
```

---

## 4. How Each Component Works Together

### 4.1 Indexing Pipeline

```
Data Source → API Client → Raw Data → Parser → Text
                                                  ↓
                                            Text Splitter
                                                  ↓
                                            Chunks (1000 chars each)
                                                  ↓
                                            OpenAI Embeddings API
                                                  ↓
                                            Vectors (1536 dimensions)
                                                  ↓
                                            PostgreSQL + pgvector
```

**Example with GitHub:**
```python
# 1. Fetch
client = GitHubClient(token)
tree = client.get_repo_tree("company", "backend")
# tree = [{"path": "src/auth.py", "type": "blob"}, ...]

# 2. Download
content = client.get_file_content("company", "backend", "src/auth.py")
# content = "def authenticate(user):\n    ..."

# 3. Create Document
doc = Document(
    page_content=content,
    metadata={"source": "src/auth.py", "repo": "company/backend"}
)

# 4. Split
splitter = RecursiveCharacterTextSplitter(chunk_size=1500)
chunks = splitter.split_documents([doc])
# chunks = [
#   Document("def authenticate(user):\n    if user.is_valid()..."),
#   Document("    return token\n\ndef logout(user)..."),
# ]

# 5. Embed & Store
embeddings = OpenAIEmbeddings()
PGVector.from_documents(
    documents=chunks,
    embedding=embeddings,
    collection_name="github_repos",
    connection=DATABASE_URL
)
```

### 4.2 Query Pipeline

```
User Query → Orchestrator → Collection Selection
                                      ↓
                            Query Embedding (OpenAI)
                                      ↓
                            Vector Search (PostgreSQL)
                                      ↓
                            Top K Documents (10-15)
                                      ↓
                            Conversation Chain
                                      ↓
                            LLM (GPT-4o-mini)
                                      ↓
                            Generated Answer
```

### 4.3 Memory Management

**Session State Structure:**
```python
st.session_state = {
    # Global state
    "connected_tools": {
        "github": True,
        "slack": True,
        "file_reader": True
    },
    "active_collections": [
        "github_repos",
        "slack_channels", 
        "document_embeddings"
    ],
    "messages": [
        {"role": "user", "content": "What is backend?"},
        {"role": "assistant", "content": "Backend is..."}
    ],
    "unified_conversation": ConversationalRetrievalChain(...),
    
    # Module-specific state
    "github_client": GitHubClient(...),
    "github_repos": [...],
    "slack_channels": [...],
    ...
}
```

**Persistence:**
- Session state: Temporary (per browser session)
- Vector database: Permanent (survives app restart)
- On app restart: Checks which collections exist in DB → Marks tools as connected

---

## 5. Models Used - Detailed Breakdown

### 5.1 OpenAI text-embedding-ada-002

**Purpose**: Convert text to vectors

**Specifications:**
- Input: Text (max 8,191 tokens)
- Output: 1536-dimensional vector
- Cost: $0.0001 per 1K tokens

**When used:**
1. **Indexing**: Every document chunk → embedding
2. **Querying**: User query → embedding

**Example:**
```python
embeddings = OpenAIEmbeddings(openai_api_key=API_KEY)

# Indexing
text = "Backend uses microservices architecture"
vector = embeddings.embed_query(text)
# vector = [0.023, -0.015, 0.042, ..., 0.018]  (1536 numbers)

# Querying
query = "How is backend structured?"
query_vector = embeddings.embed_query(query)
# query_vector = [0.021, -0.013, 0.040, ..., 0.016]  (similar to above!)
```

### 5.2 OpenAI gpt-4o-mini

**Purpose**: Generate natural language answers

**Specifications:**
- Input: Prompt (context + question)
- Output: Text answer
- Max tokens: 1500 (configured)
- Temperature: 0.3 (more deterministic, less creative)
- Cost: $0.15/1M input tokens, $0.60/1M output tokens

**When used:**
1. **Condense question**: Rephrase with chat history
2. **Generate answer**: Create response from context

**Example:**
```python
llm = ChatOpenAI(
    model_name="gpt-4o-mini",
    temperature=0.3,
    max_tokens=1500
)

prompt = """
Context: Sushma Madduru is Head - HR (Employee ID: 12)
Question: Who is the Head of HR?
Answer:
"""

response = llm.invoke(prompt)
# response = "The Head of HR is Sushma Madduru (Employee ID: 12)."
```

### 5.3 LangChain Components

**RecursiveCharacterTextSplitter:**
- Splits text intelligently (by paragraphs, sentences, then characters)
- Maintains context with overlap

**ConversationalRetrievalChain:**
- Combines retrieval + chat memory + LLM
- Handles multi-turn conversations

**PGVector:**
- LangChain wrapper for PostgreSQL + pgvector
- Handles embedding storage and similarity search

---

## 6. Tool Selection Logic - Deep Dive

### 6.1 Why Tool Selection Matters

**Problem**: Searching all collections is slow and expensive
**Solution**: Only search relevant collections

**Example:**
- Query: "Show me Slack channels"
- Without selection: Search 5 collections (slow)
- With selection: Search only slack_channels (fast)

### 6.2 Selection Algorithm

```python
def orchestrate_tools(query, active_collections):
    query_lower = query.lower()
    selected = []
    
    # Define rules
    rules = {
        "slack_channels": ["slack", "channel", "chat", "message"],
        "github_repos": ["code", "github", "repository", "commit", "bug"],
        "atlassian_docs": ["confluence", "jira", "ticket", "wiki"],
        "gdrive_docs": ["drive", "document", "sheet", "google"],
        "document_embeddings": ["file", "upload", "pdf"]
    }
    
    # Match keywords
    for collection, keywords in rules.items():
        if any(keyword in query_lower for keyword in keywords):
            # Verify collection exists
            try:
                vs = PGVector(collection_name=collection, ...)
                vs.similarity_search("test", k=1)
                selected.append(collection)
            except:
                pass  # Collection doesn't exist
    
    # Fallback: search all
    return selected if selected else active_collections
```

### 6.3 Selection Examples

**Query 1**: "What Slack channels are available?"
```python
query_lower = "what slack channels are available?"
# Matches: "slack" in slack_channels keywords
selected = ["slack_channels"]
```

**Query 2**: "Show me the authentication code in GitHub"
```python
query_lower = "show me the authentication code in github"
# Matches: "code" and "github" in github_repos keywords
selected = ["github_repos"]
```

**Query 3**: "What features are in JIRA and how are they implemented?"
```python
query_lower = "what features are in jira and how are they implemented?"
# Matches: "jira" in atlassian_docs, "implemented" suggests code
selected = ["atlassian_docs", "github_repos"]
```

**Query 4**: "Tell me about the company"
```python
query_lower = "tell me about the company"
# No keyword matches
selected = []  # Empty
# Fallback: Use all active_collections
return active_collections  # All 5 collections
```

---

## 7. Key Takeaways

### System Architecture
```
5 Data Sources → 5 Modules → 1 Vector DB (5 collections) → 
1 Orchestrator → 1 LLM → 1 Answer
```

### Data Flow
```
Connect → Fetch → Parse → Split → Embed → Store → 
Query → Search → Retrieve → Generate → Display
```

### AI Components
- **Embeddings**: text-embedding-ada-002 (1536 dimensions)
- **LLM**: gpt-4o-mini (temperature 0.3, max 1500 tokens)
- **Vector DB**: PostgreSQL + pgvector (cosine similarity)

### Intelligence
- **Orchestrator**: Keyword-based collection selection
- **Memory**: ConversationBufferMemory (full chat history)
- **RAG**: Retrieval-Augmented Generation (context + LLM)

### Performance
- **Chunking**: 1000-1500 chars with 200 overlap
- **Retrieval**: Top 5 per collection, 10-15 total
- **Caching**: Session state + persistent DB

This system enables intelligent, context-aware search across multiple data sources with conversational AI! 🚀
