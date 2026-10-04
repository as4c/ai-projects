# MCP Servers - Slack & GitHub Integration

This project provides two MCP (Model Context Protocol) servers for querying Slack channels and GitHub repositories.

## Features

### 🔹 Slack MCP Server
- Fetches all Slack channels and their descriptions
- Intelligently routes queries to appropriate channels
- Example queries:
  - "Where should I put backend related query?"
  - "Which channel for database schema questions?"

### 🔹 GitHub MCP Server
- Indexes entire GitHub repositories
- Answers questions about code structure and implementation
- Example queries:
  - "How does the order system work in this repo?"
  - "What are the table schemas used?"
  - "Explain the authentication flow"

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `DATABASE_URL`: PostgreSQL connection string with pgvector extension
- `SLACK_BOT_TOKEN`: Slack bot token (xoxb-...)
- `GITHUB_TOKEN`: GitHub personal access token

### 3. Slack Bot Setup
1. Go to https://api.slack.com/apps
2. Create a new app
3. Add OAuth scopes: `channels:read`, `groups:read`
4. Install app to workspace
5. Copy the Bot User OAuth Token

### 4. GitHub Token Setup
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token with `repo` scope
3. Copy the token

### 5. PostgreSQL with pgvector
Ensure you have PostgreSQL with pgvector extension:
```sql
CREATE EXTENSION vector;
```

## Usage

### Run MCP Streamlit App
```bash
streamlit run mcp_app.py
```

### Run Individual Servers

**Slack Server:**
```bash
python slack_mcp_server.py
```

**GitHub Server:**
```bash
python github_mcp_server.py
```

### Run Integration
```bash
python mcp_integration.py
```

## Example Queries

### Slack Queries
- "Where should I post backend related questions?"
- "Which channel for database schema discussions?"
- "Where to ask about frontend issues?"

### GitHub Queries
- "How does the authentication system work?"
- "What database tables are used in this project?"
- "Explain the order processing flow"
- "What APIs are exposed by this service?"

## Architecture

```
┌─────────────────┐
│  Streamlit UI   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼───┐
│Slack │  │GitHub│
│ MCP  │  │ MCP  │
└──────┘  └──────┘
```

## Files

- `mcp_app.py` - Main Streamlit application
- `slack_mcp_server.py` - Slack MCP server implementation
- `github_mcp_server.py` - GitHub MCP server implementation
- `mcp_integration.py` - Unified integration layer
- `app.py` - Original document chat application

## Notes

- GitHub indexing may take time for large repositories (limited to 100 files in demo)
- Slack channels are cached after first fetch
- Vector embeddings are stored in PostgreSQL for fast retrieval
