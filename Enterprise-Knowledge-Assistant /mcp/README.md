# Unified MCP Server 🚀

A unified Model Context Protocol (MCP) server that combines multiple data sources into one intelligent chat interface.

## Key Features

✅ **Unified Chat Interface** - One conversation across all your tools
✅ **Multi-Tool Context** - Connect GitHub, Confluence, JIRA, Google Drive, and more
✅ **Cross-Platform Queries** - Ask questions that span multiple data sources
✅ **Vector Search** - Powered by OpenAI embeddings and PostgreSQL

## Services Included

- **🔷 Atlassian** - Confluence docs & JIRA issues
- **🐙 GitHub** - Repository code and documentation
- **📁 Google Drive** - Documents and files
- **📚 File Reader** - Upload local documents (PDF, TXT, JSON, DOCX)
- **💬 Slack** - Channel recommendations

## Setup

1. Install dependencies:
```bash
pip install -r ../requirements.txt
```

2. Configure `.env` in parent directory:
```
OPENAI_API_KEY=your_openai_key
DATABASE_URL=postgresql://user:pass@host:5432/db
GITHUB_TOKEN=your_github_token
CONFLUENCE_URL=https://yourcompany.atlassian.net
CONFLUENCE_EMAIL=your_email
CONFLUENCE_KEY=your_api_token
SLACK_BOT_TOKEN=your_slack_token
```

3. Run:
```bash
./run.sh
# or
streamlit run app.py
```

## Usage Example

### Scenario: Understanding a Feature Across Your Stack

1. **Connect GitHub** - Index your repository
2. **Connect Atlassian** - Load Confluence docs and JIRA issues
3. **Ask unified questions:**
   - "What features are planned in JIRA and how are they implemented in the codebase?"
   - "Show me the Confluence documentation for the authentication feature and its implementation"
   - "Which JIRA tickets relate to the payment module in the GitHub repo?"

## How It Works

1. **Connect Tools** - Use sidebar expanders to connect and index data from each tool
2. **Unified Context** - All indexed data is stored in PostgreSQL with vector embeddings
3. **Smart Search** - Ask questions and the AI searches across ALL connected tools
4. **Source Attribution** - See which sources (GitHub files, Confluence pages, etc.) were used

## Architecture

- **Main App** (`app.py`) - Unified chat interface
- **Modules** - Individual tool connectors (atlassian, github, google_drive, file_reader, slack)
- **Vector Store** - PostgreSQL with pgvector for semantic search
- **LLM** - GPT-4o-mini for intelligent responses
