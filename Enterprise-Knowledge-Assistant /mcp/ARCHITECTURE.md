# Architecture Overview

## Unified MCP Server Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit UI (app.py)                   │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Unified Chat Interface                      │    │
│  │  "What features are in JIRA and how are they       │    │
│  │   implemented in GitHub?"                          │    │
│  └────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │    Unified Conversation Chain (LangChain)          │    │
│  │    - GPT-4o-mini                                   │    │
│  │    - Conversation Memory                           │    │
│  │    - Multi-source Retriever                        │    │
│  └────────────────────────────────────────────────────┘    │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   PostgreSQL + pgvector               │
        │                                        │
        │   Collections:                         │
        │   ├─ atlassian_docs (Confluence/JIRA) │
        │   ├─ github_repos (Code & Docs)       │
        │   ├─ gdrive_docs (Drive Files)        │
        │   ├─ document_embeddings (Uploads)    │
        │   └─ [Future collections...]          │
        └───────────────────────────────────────┘
                            ▲
                            │
        ┌───────────────────┴───────────────────┐
        │                                        │
┌───────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐
│   Atlassian    │  │   GitHub    │  │  Google Drive   │
│   Module       │  │   Module    │  │    Module       │
│                │  │             │  │                 │
│ • Confluence   │  │ • Repos     │  │ • Docs          │
│ • JIRA         │  │ • Files     │  │ • Sheets        │
│ • Bitbucket    │  │ • Code      │  │ • PDFs          │
└────────────────┘  └─────────────┘  └─────────────────┘
```

## Data Flow

### 1. Connection Phase
```
User → Sidebar Expander → Module.render_connection() → API Auth
```

### 2. Indexing Phase
```
Module → Fetch Data → Create Embeddings → Store in PostgreSQL
                                          → Update active_collections
                                          → Mark tool as connected
```

### 3. Query Phase
```
User Question → Unified Conversation Chain
              → Search ALL active collections
              → Retrieve relevant chunks
              → GPT generates answer
              → Display with source attribution
```

## Key Components

### Main App (`app.py`)
- Manages sidebar with tool connection status
- Hosts unified chat interface
- Creates unified retriever from all active collections
- Handles conversation flow

### Tool Modules (`modules/*.py`)
Each module provides:
- `render_connection()` - UI for connecting and indexing
- `index_to_vectorstore()` - Stores data with embeddings
- Updates `st.session_state.connected_tools`
- Adds collection name to `st.session_state.active_collections`

### Session State Structure
```python
st.session_state = {
    "connected_tools": {
        "atlassian": True,
        "github": True,
        # ... other tools
    },
    "active_collections": [
        "atlassian_docs",
        "github_repos",
        # ... other collections
    ],
    "unified_conversation": ConversationalRetrievalChain,
    "messages": [
        {"role": "user", "content": "...", "sources": [...]},
        # ... chat history
    ]
}
```

## Benefits

✅ **Single Source of Truth** - One chat interface for all data
✅ **Cross-Platform Intelligence** - AI understands context across tools
✅ **Scalable** - Easy to add new tools/modules
✅ **Persistent** - Data stored in PostgreSQL, survives restarts
✅ **Source Attribution** - Always know where answers come from
