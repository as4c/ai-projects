# Database Schema & Indexing Process

## 1. Database Schema

### 1.1 PostgreSQL with pgvector Extension

**Database**: PostgreSQL 
**Extension**: pgvector (for vector similarity search)
**Connection**: `postgresql://postgres:postgres@localhost:5433/postgres`

### 1.2 Main Tables Created by LangChain

#### Table 1: `langchain_pg_collection`
Stores collection metadata (one row per collection)

```sql
CREATE TABLE langchain_pg_collection (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL UNIQUE,
    cmetadata JSONB
);
```

**Data Example:**
```sql
uuid                                  | name                  | cmetadata
--------------------------------------|-----------------------|----------
a1b2c3d4-e5f6-7890-abcd-ef1234567890 | github_repos          | {}
b2c3d4e5-f6a7-8901-bcde-f12345678901 | atlassian_docs        | {}
c3d4e5f6-a7b8-9012-cdef-123456789012 | gdrive_docs           | {}
d4e5f6a7-b8c9-0123-def1-234567890123 | slack_channels        | {}
e5f6a7b8-c9d0-1234-ef12-345678901234 | document_embeddings   | {}
```

#### Table 2: `langchain_pg_embedding`
Stores actual document chunks with embeddings

```sql
CREATE TABLE langchain_pg_embedding (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID REFERENCES langchain_pg_collection(uuid) ON DELETE CASCADE,
    embedding VECTOR(1536),           -- 1536-dimensional vector
    document TEXT,                     -- The actual text chunk
    cmetadata JSONB                    -- Metadata (source, type, etc.)
);

-- Index for fast vector similarity search
CREATE INDEX ON langchain_pg_embedding 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Data Example:**
```sql
uuid        | collection_id | embedding                    | document                           | cmetadata
------------|---------------|------------------------------|------------------------------------|-----------
uuid1       | a1b2c3d4...   | [0.023, -0.015, 0.042, ...]  | "def authenticate(user):\n..."     | {"source": "auth.py", "type": "code", "repo": "backend"}
uuid2       | b2c3d4e5...   | [0.031, 0.022, -0.018, ...]  | "Backend Architecture Guide..."    | {"source": "Architecture", "type": "confluence"}
uuid3       | e5f6a7b8...   | [0.019, -0.012, 0.033, ...]  | "Employee ID: 12\nName: Sushma..." | {"source": "org_chart.json", "type": "document", "name": "Sushma Madduru"}
```

### 1.3 Complete Schema Visualization

```
┌─────────────────────────────────────────────────────────────┐
│              langchain_pg_collection                         │
├─────────────────────────────────────────────────────────────┤
│ uuid (PK)              | name              | cmetadata      │
├─────────────────────────────────────────────────────────────┤
│ a1b2c3d4-...           | github_repos      | {}             │
│ b2c3d4e5-...           | atlassian_docs    | {}             │
│ c3d4e5f6-...           | gdrive_docs       | {}             │
│ d4e5f6a7-...           | slack_channels    | {}             │
│ e5f6a7b8-...           | document_embeddings | {}           │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ (Foreign Key)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              langchain_pg_embedding                          │
├─────────────────────────────────────────────────────────────┤
│ uuid (PK) | collection_id (FK) | embedding | document | cmetadata │
├─────────────────────────────────────────────────────────────┤
│ uuid1     | a1b2c3d4-...       | [0.02...] | "def..." | {source, type} │
│ uuid2     | a1b2c3d4-...       | [0.03...] | "class"  | {source, type} │
│ uuid3     | b2c3d4e5-...       | [0.01...] | "Backend"| {source, type} │
│ uuid4     | e5f6a7b8-...       | [0.02...] | "Emp ID" | {source, type} │
│ ...       | ...                | ...       | ...      | ...            │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Indexing Process for All Tools

### 2.1 Generic Indexing Flow (All Tools Follow This)

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Fetch Raw Data from Source                          │
│ • API calls to external services                            │
│ • Download files, pages, code, etc.                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Parse & Transform to Text                           │
│ • HTML → Text (BeautifulSoup)                               │
│ • PDF → Text (PyPDFLoader)                                  │
│ • JSON → Formatted Text                                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Create LangChain Documents                          │
│ Document(page_content=text, metadata={...})                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Split into Chunks                                   │
│ RecursiveCharacterTextSplitter(chunk_size=1000-1500)        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Generate Embeddings                                 │
│ OpenAI API: text → [1536 numbers]                           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Store in PostgreSQL                                 │
│ PGVector.from_documents(collection_name="...")               │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Tool-Specific Indexing Details

### 3.1 Atlassian (Confluence/JIRA)

**Collection Name**: `atlassian_docs`

**Indexing Code:**
```python
def index_to_vectorstore(items_data):
    # Step 1: Create Documents
    all_docs = []
    for item in items_data:
        doc = Document(
            page_content=item['content'],  # Parsed HTML text
            metadata={
                'source': item['title'],    # "Backend Architecture"
                'type': item['type']        # "confluence" or "jira"
            }
        )
        all_docs.append(doc)
    
    # Step 2: Split into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(all_docs)
    
    # Step 3: Generate embeddings & store
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    PGVector.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name="atlassian_docs",
        connection=DATABASE_URL,
        pre_delete_collection=False  # Append mode
    )
```

**What Gets Stored:**
```sql
-- Example row in langchain_pg_embedding
{
    "uuid": "abc123...",
    "collection_id": "b2c3d4e5...",  -- atlassian_docs collection
    "embedding": [0.031, 0.022, -0.018, ...],  -- 1536 numbers
    "document": "Backend Architecture Guide\n\nOur backend uses microservices...",
    "cmetadata": {
        "source": "Backend Architecture",
        "type": "confluence"
    }
}
```

**Data Flow:**
```
Confluence API → HTML → BeautifulSoup → Plain Text → 
Document → Chunks → Embeddings → PostgreSQL
```

---

### 3.2 GitHub

**Collection Name**: `github_repos`

**Indexing Code:**
```python
# In github.py module
tree = client.get_repo_tree(owner, repo)  # Get all files
files_to_process = [f for f in tree if should_process_file(f['path'])]

repo_files = []
for file_info in files_to_process[:100]:  # Limit 100 files
    content = client.get_file_content(owner, repo, file_info['path'])
    if content:
        repo_files.append({
            'path': file_info['path'],
            'content': content
        })

# Create documents
documents = [
    Document(
        page_content=f['content'],
        metadata={
            'source': f['path'],           # "src/auth.py"
            'repo': repo_name,             # "company/backend"
            'type': 'code'
        }
    ) for f in repo_files
]

# Split & store
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
chunks = text_splitter.split_documents(documents)

embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
PGVector.from_documents(
    documents=chunks,
    embedding=embeddings,
    collection_name="github_repos",
    connection=DATABASE_URL,
    pre_delete_collection=False
)
```

**What Gets Stored:**
```sql
{
    "uuid": "def456...",
    "collection_id": "a1b2c3d4...",  -- github_repos collection
    "embedding": [0.023, -0.015, 0.042, ...],
    "document": "def authenticate(user):\n    if user.is_valid():\n        return generate_token(user)\n    raise AuthError()",
    "cmetadata": {
        "source": "src/auth.py",
        "repo": "company/backend",
        "type": "code"
    }
}
```

**Data Flow:**
```
GitHub API → Base64 Content → Decode → Text → 
Filter Files → Document → Chunks → Embeddings → PostgreSQL
```

---

### 3.3 Google Drive

**Collection Name**: `gdrive_docs`

**Indexing Code:**
```python
# Download files
files_data = []
for file in selected_files:
    if file['mimeType'] == 'application/vnd.google-apps.document':
        content = service.export_google_doc(file['id'], 'text/plain')
        file_name = file['name'] + '.txt'
    elif file['mimeType'] == 'application/vnd.google-apps.spreadsheet':
        content = service.export_google_doc(file['id'], 'text/csv')
        file_name = file['name'] + '.csv'
    else:
        content = service.download_file(file['id'])
        file_name = file['name']
    
    files_data.append({'name': file_name, 'content': content})

# Process files
all_docs = []
for file_data in files_data:
    # Use appropriate loader (PDF, DOCX, TXT)
    docs = process_file_content(file_data['name'], file_data['content'])
    for doc in docs:
        doc.metadata['source'] = file_data['name']
        doc.metadata['type'] = 'document'
    all_docs.extend(docs)

# Split & store
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = text_splitter.split_documents(all_docs)

embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
PGVector.from_documents(
    documents=chunks,
    embedding=embeddings,
    collection_name="gdrive_docs",
    connection=DATABASE_URL,
    pre_delete_collection=False
)
```

**What Gets Stored:**
```sql
{
    "uuid": "ghi789...",
    "collection_id": "c3d4e5f6...",  -- gdrive_docs collection
    "embedding": [0.041, -0.028, 0.015, ...],
    "document": "Product Requirements Document\n\nFeature: User Authentication\nDescription: Implement OAuth2...",
    "cmetadata": {
        "source": "Product_Requirements.pdf",
        "type": "document"
    }
}
```

**Data Flow:**
```
Google Drive API → Export/Download → Parse (PDF/DOCX) → 
Text → Document → Chunks → Embeddings → PostgreSQL
```

---

### 3.4 Slack

**Collection Name**: `slack_channels`

**Indexing Code:**
```python
def store_channels_in_db(channels, embeddings_model):
    documents = []
    
    for ch in channels:
        # Create rich description
        content = f"""Slack Channel: #{ch['name']}
Description: {ch['description']}
Topic: {ch['topic']}

This is a Slack channel for {ch['description']}. 
Use this channel for discussions about {ch['topic']}."""
        
        doc = Document(
            page_content=content,
            metadata={
                "source": f"#{ch['name']}",
                "type": "slack_channel",
                "channel_name": ch['name'],
                "description": ch['description'],
                "topic": ch['topic']
            }
        )
        documents.append(doc)
    
    # Store (no splitting needed - channels are small)
    vectorstore = PGVector.from_documents(
        documents=documents,
        embedding=embeddings_model,
        collection_name="slack_channels",
        connection=DATABASE_URL,
        pre_delete_collection=True  # Replace mode
    )
```

**What Gets Stored:**
```sql
{
    "uuid": "jkl012...",
    "collection_id": "d4e5f6a7...",  -- slack_channels collection
    "embedding": [0.019, -0.012, 0.033, ...],
    "document": "Slack Channel: #backend\nDescription: Backend development, APIs, databases\nTopic: Java, Python, Node.js\n\nThis is a Slack channel for Backend development...",
    "cmetadata": {
        "source": "#backend",
        "type": "slack_channel",
        "channel_name": "backend",
        "description": "Backend development, APIs, databases",
        "topic": "Java, Python, Node.js"
    }
}
```

**Data Flow:**
```
Slack API → Channel List → Format Description → 
Document → Embeddings → PostgreSQL (no splitting)
```

---

### 3.5 File Reader (Uploaded Files)

**Collection Name**: `document_embeddings`

**Indexing Code:**
```python
def index_document(uploaded_file, description=""):
    # Step 1: Load document
    documents = load_document(uploaded_file)  # Uses appropriate loader
    
    # Step 2: Add metadata
    for doc in documents:
        doc.metadata['type'] = 'document'
        doc.metadata['source'] = uploaded_file.name
        
        if description:
            doc.metadata['description'] = description
            # Add description to content for better search
            doc.page_content = f"[File: {uploaded_file.name} - {description}]\n\n{doc.page_content}"
    
    # Step 3: Split
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(documents)
    
    # Step 4: Store
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    PGVector.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name="document_embeddings",
        connection=DATABASE_URL,
        pre_delete_collection=False
    )
```

**Special: JSON File Handling**
```python
# For org_chart.json
def format_record(item):
    return f"""Employee ID: {item['emp_id']}
Name: {item['name']}
Designation: {item['designation']}
Department: {item['department']}
Email: {item['email']}
Manager ID: {item['manager_id']}
Location: {item['location']}"""

# Each employee becomes a separate document
for employee in data['data']:
    text = format_record(employee)
    doc = Document(
        page_content=text,
        metadata={
            'source': 'org_chart.json',
            'name': employee['name']
        }
    )
```

**What Gets Stored:**
```sql
{
    "uuid": "mno345...",
    "collection_id": "e5f6a7b8...",  -- document_embeddings collection
    "embedding": [0.019, -0.012, 0.033, ...],
    "document": "[File: org_chart.json - Employee org chart]\n\nEmployee ID: 12\nName: Sushma Madduru\nDesignation: Head - HR\nDepartment: HR\nEmail: sushma@getlokalapp.com\nManager ID: 5\nLocation: Bangalore",
    "cmetadata": {
        "source": "org_chart.json",
        "type": "document",
        "description": "Employee org chart",
        "name": "Sushma Madduru"
    }
}
```

**Data Flow:**
```
File Upload → Detect Type → Parse (PDF/JSON/DOCX/TXT) → 
Format → Add Description → Document → Chunks → Embeddings → PostgreSQL
```

---

## 4. Indexing Comparison Table

| Tool | Collection | Chunk Size | Special Processing | Metadata Fields |
|------|-----------|------------|-------------------|-----------------|
| **Atlassian** | atlassian_docs | 1000 | HTML → Text (BeautifulSoup) | source, type |
| **GitHub** | github_repos | 1500 | Base64 decode, File filtering | source, repo, type |
| **Google Drive** | gdrive_docs | 1000 | Export Google Docs, Parse PDFs | source, type |
| **Slack** | slack_channels | No split | Rich description format | source, type, channel_name, description, topic |
| **File Reader** | document_embeddings | 1000 | JSON formatting, Description prefix | source, type, description, name |

---

## 5. Database Queries

### 5.1 View All Collections
```sql
SELECT * FROM langchain_pg_collection;
```

### 5.2 Count Documents per Collection
```sql
SELECT 
    c.name AS collection_name,
    COUNT(e.uuid) AS document_count
FROM langchain_pg_collection c
LEFT JOIN langchain_pg_embedding e ON c.uuid = e.collection_id
GROUP BY c.name;
```

**Example Output:**
```
collection_name      | document_count
---------------------|---------------
github_repos         | 245
atlassian_docs       | 87
gdrive_docs          | 34
slack_channels       | 12
document_embeddings  | 156
```

### 5.3 View Sample Documents from a Collection
```sql
SELECT 
    LEFT(e.document, 100) AS document_preview,
    e.cmetadata
FROM langchain_pg_embedding e
JOIN langchain_pg_collection c ON e.collection_id = c.uuid
WHERE c.name = 'document_embeddings'
LIMIT 5;
```

### 5.4 Search by Metadata
```sql
SELECT 
    e.document,
    e.cmetadata->>'source' AS source,
    e.cmetadata->>'type' AS type
FROM langchain_pg_embedding e
JOIN langchain_pg_collection c ON e.collection_id = c.uuid
WHERE c.name = 'document_embeddings'
  AND e.cmetadata->>'name' LIKE '%Sushma%';
```

### 5.5 Delete a Collection
```sql
-- Delete all embeddings in a collection
DELETE FROM langchain_pg_embedding
WHERE collection_id = (
    SELECT uuid FROM langchain_pg_collection 
    WHERE name = 'document_embeddings'
);

-- Delete the collection itself
DELETE FROM langchain_pg_collection 
WHERE name = 'document_embeddings';
```

---

## 6. Vector Search Internals

### 6.1 How Similarity Search Works

```sql
-- This is what happens internally when you call:
-- vectorstore.similarity_search("backend architecture", k=5)

SELECT 
    e.document,
    e.cmetadata,
    1 - (e.embedding <=> '[0.023, -0.015, ...]'::vector) AS similarity
FROM langchain_pg_embedding e
JOIN langchain_pg_collection c ON e.collection_id = c.uuid
WHERE c.name = 'github_repos'
ORDER BY e.embedding <=> '[0.023, -0.015, ...]'::vector
LIMIT 5;
```

**Operators:**
- `<=>` : Cosine distance (lower = more similar)
- `<->` : L2 distance (Euclidean)
- `<#>` : Inner product

### 6.2 Index Types

**IVFFlat Index** (used by default):
```sql
CREATE INDEX ON langchain_pg_embedding 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

- **lists**: Number of clusters (100 is default)
- **Tradeoff**: Speed vs accuracy
- **Best for**: Medium-sized datasets (< 1M vectors)

---

## 7. Storage Estimates

### 7.1 Size Calculation

**Per Document Chunk:**
- Embedding: 1536 floats × 4 bytes = 6,144 bytes (~6 KB)
- Text: Variable (avg ~500 bytes)
- Metadata: Variable (avg ~200 bytes)
- **Total**: ~7 KB per chunk

**Example:**
- 1000 chunks = ~7 MB
- 10,000 chunks = ~70 MB
- 100,000 chunks = ~700 MB

### 7.2 Current System Estimate

Assuming:
- GitHub: 100 files × 3 chunks = 300 chunks
- Atlassian: 20 pages × 5 chunks = 100 chunks
- Google Drive: 10 files × 4 chunks = 40 chunks
- Slack: 12 channels × 1 chunk = 12 chunks
- File Reader: 5 files × 10 chunks = 50 chunks

**Total**: ~500 chunks = ~3.5 MB

---

## 8. Key Takeaways

### Schema Summary
```
2 Tables:
├── langchain_pg_collection (5 rows - one per tool)
└── langchain_pg_embedding (hundreds/thousands of rows - document chunks)
```

### Indexing Pattern (All Tools)
```
Fetch → Parse → Document → Split → Embed → Store
```

### Storage Structure
```
Collection → Many Chunks → Each has (embedding, text, metadata)
```

### Search Mechanism
```
Query → Embedding → Vector Similarity → Top K Chunks → LLM
```

This database design enables fast, scalable semantic search across all your data sources! 🚀
