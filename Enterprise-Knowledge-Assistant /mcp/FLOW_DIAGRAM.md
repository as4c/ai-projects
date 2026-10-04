# MCP System Flow Diagrams

## 1. Application Startup Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Start                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Load Environment Variables                      │
│  • OPENAI_API_KEY  • DATABASE_URL  • API_TOKENS             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│           Initialize Session State                           │
│  • connected_tools = {}                                      │
│  • active_collections = []                                   │
│  • messages = []                                             │
│  • unified_conversation = None                               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│         Load Persisted State from Database                   │
│  Check each collection: atlassian_docs, github_repos, etc.  │
│  If exists → Mark tool as connected                          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Render Streamlit UI                             │
│  • Sidebar (Tool Connections)                                │
│  • Main Chat Interface                                       │
└─────────────────────────────────────────────────────────────┘
```

## 2. Tool Connection Flow (Generic)

```
┌─────────────────────────────────────────────────────────────┐
│         User Clicks "Connect" in Sidebar                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│          Module: render_connection()                         │
│  • Collect credentials (API tokens, URLs)                    │
│  • Initialize API client                                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Authenticate & Fetch Data                       │
│  • Test API connection                                       │
│  • Fetch available resources (repos, files, channels, etc.) │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│           User Selects Items to Index                        │
│  • Repos, Files, Pages, Channels                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│         Click "Index to Unified Chat"                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Process & Transform Data                        │
│  • Download content                                          │
│  • Parse (HTML, JSON, PDF, etc.)                             │
│  • Create LangChain Documents                                │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Text Splitting                                  │
│  RecursiveCharacterTextSplitter                              │
│  • chunk_size: 1000-1500                                     │
│  • chunk_overlap: 200                                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│           Generate Embeddings (OpenAI)                       │
│  • Model: text-embedding-ada-002                             │
│  • Dimension: 1536                                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│         Store in PGVector Database                           │
│  • Collection: [tool_name]_[type]                            │
│  • Metadata: source, type, etc.                              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│          Update Session State                                │
│  • connected_tools["tool_name"] = True                       │
│  • active_collections.append("collection_name")              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Show Success Message                            │
└─────────────────────────────────────────────────────────────┘
```

## 3. Query Processing Flow

```
┌─────────────────────────────────────────────────────────────┐
│         User Enters Query in Chat Input                      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│       Add Message to Session State                           │
│  messages.append({"role": "user", "content": query})         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│      Update Unified Conversation Chain                       │
│  • Create unified vectorstore                                │
│  • Initialize ConversationalRetrievalChain                   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Orchestrator Analysis                           │
│  orchestrate_tools(query, active_collections)                │
│  • Parse query keywords                                      │
│  • Match to collection rules                                 │
│  • Select relevant collections                               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│         Multi-Collection Semantic Search                     │
│  For each selected collection:                               │
│  • Generate query embedding                                  │
│  • Vector similarity search (k=5 per collection)             │
│  • Aggregate results (total k=10-15)                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Retrieval Results                               │
│  • Ranked documents by similarity                            │
│  • Metadata: source, type, collection                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│         ConversationalRetrievalChain                         │
│  1. Condense question with chat history                      │
│  2. Retrieve relevant documents                              │
│  3. Generate answer with context                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              LLM Processing (GPT-4o-mini)                    │
│  • Context: Retrieved documents                              │
│  • History: Previous conversation                            │
│  • Prompt: Custom QA template                                │
│  • Temperature: 0.3                                          │
│  • Max tokens: 1500                                          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Generate Response                               │
│  • Answer text                                               │
│  • Source documents                                          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│         Display Response in Chat                             │
│  • Show answer                                               │
│  • Show source count & types                                 │
│  • Add to message history                                    │
└─────────────────────────────────────────────────────────────┘
```

## 4. Module-Specific Flows

### 4.1 Atlassian (Confluence) Flow

```
Connect → Authenticate → List Spaces → Select Space → 
Load Pages → Select Pages → Fetch Content (HTML) → 
Parse with BeautifulSoup → Create Documents → 
Split Text → Embed → Store in atlassian_docs
```

### 4.2 GitHub Flow

```
Method Selection (Token/URL) →
  [Token]: Fetch User Repos → Select Repo
  [URL]: Parse URL → Extract owner/repo
→ Get Repo Tree (recursive) → Filter Files (code/docs) →
Download File Content → Create Documents → 
Split Text → Embed → Store in github_repos
```

### 4.3 Google Drive Flow

```
OAuth Authentication → List Files/Folders → 
Navigate Folders → Select Items → 
Expand Folders (recursive) → Download Files →
  [Google Docs]: Export as text
  [Sheets]: Export as CSV
  [Others]: Direct download
→ Process with Loaders → Create Documents → 
Split Text → Embed → Store in gdrive_docs
```

### 4.4 Slack Flow

```
Load Channels (Real API/Hardcoded) → 
Generate Channel Descriptions → 
Create Channel Documents → 
Embed Channel Info → Store in slack_channels →
Query Matching: Semantic search for relevant channels
```

### 4.5 File Reader Flow

```
Upload File → Detect Type (PDF/TXT/JSON/DOCX) →
Load with Appropriate Loader →
  [JSON]: Custom formatting for structured data
  [PDF]: PyPDFLoader
  [DOCX]: Docx2txtLoader
  [TXT]: TextLoader
→ Add Description to Metadata → 
Split Text → Embed → Store in document_embeddings
```

## 5. Orchestrator Logic Flow

```
┌─────────────────────────────────────────────────────────────┐
│              Receive User Query                              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│         Keyword Matching Rules                               │
│                                                              │
│  slack_channels:                                             │
│    ["slack", "channel", "chat", "message"]                   │
│                                                              │
│  github_repos:                                               │
│    ["code", "github", "repository", "bug"]                   │
│                                                              │
│  atlassian_docs:                                             │
│    ["confluence", "jira", "ticket", "wiki"]                  │
│                                                              │
│  gdrive_docs:                                                │
│    ["drive", "document", "sheet", "google"]                  │
│                                                              │
│  document_embeddings:                                        │
│    ["file", "upload", "pdf"]                                 │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│         Match Query to Collections                           │
│  • Convert query to lowercase                                │
│  • Check for keyword presence                                │
│  • Verify collection exists in DB                            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Return Selected Collections                     │
│  If no match → Use all active_collections                    │
└─────────────────────────────────────────────────────────────┘
```

## 6. Error Handling Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   Error Occurs                               │
└─────────────────────────────────────────────────────────────┘
                          │
                ┌─────────┴─────────┐
                │                   │
                ▼                   ▼
┌──────────────────────┐  ┌──────────────────────┐
│   API Errors         │  │   OpenAI Errors      │
│ • Auth failures      │  │ • Rate limits        │
│ • Network issues     │  │ • Quota exceeded     │
│ • Invalid tokens     │  │ • Token limits       │
└──────────────────────┘  └──────────────────────┘
                │                   │
                └─────────┬─────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Display Error Message                           │
│  • User-friendly message                                     │
│  • Actionable suggestions                                    │
│  • Log technical details                                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│         Maintain Application State                           │
│  • Don't crash                                               │
│  • Keep existing connections                                 │
│  • Allow retry                                               │
└─────────────────────────────────────────────────────────────┘
```

## 7. Session State Management

```
Session State Structure:
├── connected_tools: {tool_name: bool}
├── active_collections: [collection_names]
├── messages: [{role, content, sources}]
├── unified_conversation: ConversationalRetrievalChain
├── token_usage: {total, prompt, completion}
│
├── atlassian_*: {service, connected, selected_items, service_type}
├── github_*: {client, repos}
├── gdrive_*: {service, authenticated, selected_items, current_folder}
├── slack_*: {channels, channel_embeddings, embeddings_model}
└── file_reader_*: {processed_file}
```

## Key Performance Considerations

1. **Lazy Loading**: Collections loaded only when needed
2. **Batch Processing**: Multiple files processed in batches
3. **Caching**: Session state persists across interactions
4. **Pagination**: Large datasets fetched in pages
5. **Filtering**: Only relevant files indexed (skip node_modules, etc.)
6. **Chunking**: Large documents split for better retrieval
7. **Token Management**: Monitor OpenAI API usage
