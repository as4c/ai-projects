# UI Layout

## Main Interface

```
┌─────────────────────────────────────────────────────────────────────┐
│                    🚀 MCP Server - Unified Chat                     │
├──────────────────┬──────────────────────────────────────────────────┤
│                  │                                                   │
│  SIDEBAR         │           MAIN CHAT AREA                         │
│                  │                                                   │
│ Connected Tools  │  💬 Unified Chat Interface                       │
│ ⚪ 🔷 Atlassian  │  Active Tools: GitHub, Atlassian                 │
│ ✅ 🐙 GitHub     │  ─────────────────────────────────────────────   │
│ ⚪ 📁 Drive      │                                                   │
│ ⚪ 📚 File       │  👤 User                                          │
│ ⚪ 💬 Slack      │  What features are planned in JIRA and           │
│                  │  implemented in GitHub?                          │
│ ───────────────  │                                                   │
│                  │  🤖 Assistant                                     │
│ Connect Tools    │  Based on JIRA and GitHub, here are the         │
│                  │  features:                                        │
│ ▼ 🔷 Atlassian  │  1. Authentication (JIRA-123)                    │
│   Service: ●     │     - Implemented in src/auth/                   │
│   [Confluence]   │     - Status: Complete                           │
│   URL: [____]    │  2. Payment Gateway (JIRA-456)                   │
│   Email: [___]   │     - In progress                                │
│   Token: [***]   │     - Code in src/payment/                       │
│   [Connect]      │                                                   │
│                  │  📚 Sources                                       │
│ ▶ 🐙 GitHub     │  • JIRA-123 (jira)                               │
│                  │  • src/auth/oauth.py (code)                      │
│ ▶ 📁 Drive      │  • JIRA-456 (jira)                               │
│                  │                                                   │
│ ▶ 📚 File       │  👤 User                                          │
│                  │  Show me the code for authentication             │
│ ▶ 💬 Slack      │                                                   │
│                  │  🤖 Assistant                                     │
│ ───────────────  │  Here's the authentication code from             │
│                  │  src/auth/oauth.py:                              │
│ [🔄 Refresh]    │  ```python                                        │
│                  │  def authenticate(user):                         │
│                  │      # OAuth2.0 implementation                   │
│                  │  ```                                              │
│                  │                                                   │
│                  │  ┌─────────────────────────────────────┐        │
│                  │  │ Ask about your connected tools...   │        │
│                  │  └─────────────────────────────────────┘        │
│                  │                                                   │
└──────────────────┴──────────────────────────────────────────────────┘
```

## Sidebar Sections

### 1. Connected Tools Status (Top)
```
✅ 🔷 Atlassian    ← Green checkmark = connected
✅ 🐙 GitHub
⚪ 📁 Google Drive ← Gray circle = not connected
⚪ 📚 File Reader
⚪ 💬 Slack
```

### 2. Connect Tools (Expandable)
Each tool has an expander:

```
▼ 🔷 Atlassian (Expanded)
  ┌─────────────────────────┐
  │ Service: [Confluence ▼] │
  │ URL: [____________]     │
  │ Email: [__________]     │
  │ Token: [**********]     │
  │ [Connect]               │
  │                         │
  │ Space: [Docs ▼]        │
  │ [Load Pages]            │
  │                         │
  │ ☑ Feature Docs          │
  │ ☑ API Guide             │
  │ ☐ Meeting Notes         │
  │                         │
  │ [Index to Unified Chat] │
  └─────────────────────────┘

▶ 🐙 GitHub (Collapsed)

▶ 📁 Google Drive (Collapsed)
```

### 3. Refresh Button (Bottom)
```
┌─────────────────────┐
│  🔄 Refresh Context │
└─────────────────────┘
```

## Main Chat Area

### Header
```
💬 Unified Chat Interface
Active Tools: GitHub, Atlassian
─────────────────────────────────
```

### Chat Messages
```
👤 User Message
   Question text here...

🤖 Assistant Message
   Answer text here...
   
   📚 Sources (expandable)
   • source1.py (code)
   • JIRA-123 (jira)
```

### Input Box (Bottom)
```
┌──────────────────────────────────────┐
│ Ask about your connected tools...    │
└──────────────────────────────────────┘
```

## Connection Flow UI

### Before Connection
```
▼ 🔷 Atlassian
  Service: [Confluence ▼]
  URL: [____________]
  Email: [__________]
  Token: [**********]
  
  [Connect] ← Blue button
```

### After Connection
```
▼ 🔷 Atlassian
  ✅ Connected to Confluence
  
  Space: [Product Docs ▼]
  [Load Pages]
  
  Pages loaded: 15
  ☑ Authentication Guide
  ☑ API Documentation
  ☑ Architecture Overview
  
  [Index to Unified Chat] ← Primary button
  [Disconnect] ← Secondary button
```

### After Indexing
```
▼ 🔷 Atlassian
  ✅ Connected to Confluence
  ✅ Indexed 3 pages!
  
  [Disconnect]
```

## Status Indicators

### Tool Status
- ⚪ Not connected
- ✅ Connected and indexed
- 🔄 Loading/Indexing (spinner)
- ❌ Error

### Chat Status
- 💬 Ready to chat
- 🤖 Thinking... (spinner)
- ⚠️ No data available
- ✅ Response complete

## Responsive Behavior

### Desktop (Wide)
- Sidebar: 25% width
- Chat: 75% width

### Tablet (Medium)
- Sidebar: 30% width
- Chat: 70% width

### Mobile (Narrow)
- Sidebar: Collapsible
- Chat: Full width
