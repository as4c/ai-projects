# MCP System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STREAMLIT WEB APPLICATION                          │
│                                  (app.py)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
        ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐
        │   SIDEBAR UI     │  │  MAIN CHAT   │  │ SESSION STATE│
        │  (Tool Connect)  │  │  INTERFACE   │  │  MANAGEMENT  │
        └──────────────────┘  └──────────────┘  └──────────────┘
                    │                 │                 │
                    └─────────────────┼─────────────────┘
                                      │
        ┌─────────────────────────────┴─────────────────────────────┐
        │                    MODULE LAYER                            │
        │                   (modules/*.py)                           │
        └────────────────────────────────────────────────────────────┘
                │           │           │           │           │
        ┌───────▼───┐ ┌─────▼────┐ ┌───▼────┐ ┌───▼────┐ ┌────▼────┐
        │Atlassian  │ │  GitHub  │ │ GDrive │ │  Slack │ │  File   │
        │  Module   │ │  Module  │ │ Module │ │ Module │ │ Reader  │
        └───────────┘ └──────────┘ └────────┘ └────────┘ └─────────┘
                │           │           │           │           │
        ┌───────▼───────────▼───────────▼───────────▼───────────▼───┐
        │              EXTERNAL API INTEGRATIONS                     │
        ├────────────────────────────────────────────────────────────┤
        │ • Confluence API    • GitHub API      • Google Drive API   │
        │ • JIRA API          • Slack API       • File System        │
        └────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
        ┌───────────▼──────┐  ┌───────▼────────┐  ┌────▼──────────┐
        │   LANGCHAIN      │  │  OPENAI API    │  │  POSTGRESQL   │
        │   FRAMEWORK      │  │  (Embeddings   │  │  (PGVector)   │
        │                  │  │   & Chat)      │  │               │
        └──────────────────┘  └────────────────┘  └───────────────┘
                │                     │                    │
                └─────────────────────┼────────────────────┘
                                      │
        ┌─────────────────────────────▼─────────────────────────────┐
        │              VECTOR DATABASE COLLECTIONS                   │
        ├────────────────────────────────────────────────────────────┤
        │ • atlassian_docs      • github_repos                       │
        │ • gdrive_docs         • slack_channels                     │
        │ • document_embeddings                                      │
        └────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
        ┌───────────▼──────┐  ┌───────▼────────┐  ┌────▼──────────┐
        │  ORCHESTRATOR    │  │   RETRIEVER    │  │  CONVERSATION │
        │  (Query Router)  │  │   (Semantic    │  │    CHAIN      │
        │                  │  │    Search)     │  │   (RAG)       │
        └──────────────────┘  └────────────────┘  └───────────────┘
                                      │
                                      ▼
                            ┌──────────────────┐
                            │  CHAT RESPONSE   │
                            │  WITH SOURCES    │
                            └──────────────────┘
```

## Component Details

### 1. **Application Layer (app.py)**
- Main Streamlit application
- Manages UI layout (sidebar + main chat)
- Handles session state persistence
- Coordinates all modules

### 2. **Module Layer (modules/*.py)**
Each module provides:
- Connection UI rendering
- API client initialization
- Data fetching and processing
- Vector indexing

**Modules:**
- `atlassian.py` - Confluence & JIRA integration
- `github.py` - GitHub repository indexing
- `google_drive.py` - Google Drive file processing
- `slack.py` - Slack channel indexing
- `file_reader.py` - Local file upload & processing

### 3. **Integration Layer**
- External API clients (REST APIs)
- Authentication handling
- Data transformation

### 4. **AI/ML Layer**
- **LangChain**: Document processing, text splitting, RAG chain
- **OpenAI**: Embeddings (text-embedding-ada-002) & Chat (GPT-4o-mini)
- **PGVector**: Vector similarity search

### 5. **Storage Layer**
- PostgreSQL with pgvector extension
- 5 separate collections for different data sources
- Persistent storage across sessions

### 6. **Intelligence Layer**
- **Orchestrator**: Routes queries to relevant collections
- **Retriever**: Semantic search across collections
- **Conversation Chain**: RAG-based Q&A with memory

## Data Flow

```
User Query → Orchestrator → Multi-Collection Search → LLM → Response
     ↓                              ↓
Session State              Vector Embeddings
```

## Key Technologies

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| Backend | Python 3.x |
| AI Framework | LangChain |
| LLM | OpenAI GPT-4o-mini |
| Embeddings | OpenAI text-embedding-ada-002 |
| Vector DB | PostgreSQL + pgvector |
| APIs | REST (GitHub, Slack, Confluence, JIRA, Google Drive) |
