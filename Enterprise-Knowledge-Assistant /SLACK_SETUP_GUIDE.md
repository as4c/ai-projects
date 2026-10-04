# Quick Setup Guide - Slack MCP Server

## Step 1: Get Slack Bot Token

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name it (e.g., "Channel Helper") and select your workspace
4. Go to "OAuth & Permissions" in the left sidebar
5. Scroll to "Scopes" → "Bot Token Scopes"
6. Add these scopes:
   - `channels:read`
   - `groups:read`
7. Scroll up and click "Install to Workspace"
8. Copy the "Bot User OAuth Token" (starts with `xoxb-`)

## Step 2: Update .env File

Open your `.env` file and add:
```
SLACK_BOT_TOKEN=xoxb-your-token-here
```

## Step 3: Install Dependencies

```bash
pip install slack-sdk requests
```

## Step 4: Run the Streamlit App

```bash
streamlit run mcp_app.py
```

## Step 5: Use It

1. In the sidebar, click "Fetch Slack Channels"
2. Ask questions like:
   - "Where should I post backend related queries?"
   - "Which channel for database questions?"

That's it! 🎉
