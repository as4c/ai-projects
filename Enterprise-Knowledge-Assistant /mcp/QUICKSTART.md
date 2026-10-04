# Quick Start Guide

## 🚀 Get Started in 3 Minutes

### Step 1: Run the App
```bash
cd /Users/mac/Documents/hackathon/mcp
./run.sh
```

### Step 2: Connect Your First Tool

#### Option A: GitHub (Easiest)
1. Click **🐙 GitHub** in sidebar
2. Paste your GitHub token (or use .env)
3. Click "Fetch Repos"
4. Select a repository
5. Click "Index to Unified Chat"
6. ✅ Done! Start asking questions

#### Option B: File Reader (No Setup)
1. Click **📚 File Reader** in sidebar
2. Upload a PDF, TXT, or DOCX file
3. Click "Index to Unified Chat"
4. ✅ Done! Ask questions about your document

### Step 3: Ask Questions
```
"What is this project about?"
"Show me the main features"
"Explain the architecture"
```

## 🎯 Your Use Case: Feature Discovery

### Goal
Understand features across GitHub, Confluence, and JIRA

### Setup (5 minutes)

1. **Connect GitHub**
   ```
   Sidebar → 🐙 GitHub → Enter token → Fetch Repos
   → Select your repo → Index to Unified Chat
   ```

2. **Connect Atlassian (Confluence)**
   ```
   Sidebar → 🔷 Atlassian → Enter credentials
   → Select "Confluence" → Choose space → Load Pages
   → Select relevant pages → Index to Unified Chat
   ```

3. **Connect Atlassian (JIRA)**
   ```
   Same as above, but select "Jira" → Choose project
   → Load Issues → Index to Unified Chat
   ```

### Example Questions
```
✅ "What features are planned in JIRA?"
✅ "How is authentication implemented in the codebase?"
✅ "Show me Confluence documentation for the payment feature"
✅ "Which JIRA tickets relate to the API module in GitHub?"
✅ "What's the status of feature X across all platforms?"
```

## 📊 Status Indicators

### Sidebar Status
- ⚪ Not connected
- ✅ Connected and indexed

### Active Tools Display
Shows which tools are currently providing context:
```
Active Tools: GitHub, Atlassian
```

## 🔄 Refresh Context

After connecting new tools, click:
```
🔄 Refresh Context
```

This updates the unified conversation to include all connected tools.

## 💡 Pro Tips

### 1. Connect Multiple Tools First
Connect all your tools BEFORE asking questions for best results.

### 2. Use Specific Questions
❌ "Tell me about the project"
✅ "What authentication methods are in the GitHub repo?"

### 3. Check Sources
Expand "📚 Sources" under each answer to see where information came from.

### 4. Iterate
Ask follow-up questions to drill deeper:
```
Q1: "What is feature X?"
Q2: "Show me the code for that"
Q3: "Are there any bugs reported?"
```

## 🐛 Troubleshooting

### "No data available"
- Make sure you clicked "Index to Unified Chat" for at least one tool
- Click "🔄 Refresh Context" button

### "Connection failed"
- Check your credentials in .env file
- Verify API tokens are valid
- Check network connection

### "No results found"
- Try rephrasing your question
- Make sure relevant data was indexed
- Check if the right tools are connected

## 📝 Environment Variables

Create `.env` in parent directory:
```bash
# Required
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...

# Optional (for specific tools)
GITHUB_TOKEN=ghp_...
CONFLUENCE_URL=https://yourcompany.atlassian.net
CONFLUENCE_EMAIL=you@company.com
CONFLUENCE_KEY=...
SLACK_BOT_TOKEN=xoxb-...
```

## 🎓 Next Steps

1. ✅ Connect your first tool
2. ✅ Ask basic questions
3. ✅ Connect additional tools
4. ✅ Ask cross-platform questions
5. ✅ Read [EXAMPLES.md](EXAMPLES.md) for advanced use cases
6. ✅ Check [ARCHITECTURE.md](ARCHITECTURE.md) to understand how it works

## 🆘 Need Help?

- Check [README.md](README.md) for detailed setup
- See [EXAMPLES.md](EXAMPLES.md) for use case examples
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
