# Example Use Cases

## Use Case 1: Feature Discovery Across Stack

### Scenario
You want to understand how a specific feature is documented, planned, and implemented across your organization.

### Steps
1. **Connect Atlassian (Confluence)**
   - Select your product documentation space
   - Index pages related to features

2. **Connect Atlassian (JIRA)**
   - Load issues from your project
   - Index feature tickets and bugs

3. **Connect GitHub**
   - Select your main repository
   - Index codebase

### Example Questions
```
Q: "What is the authentication feature and how is it implemented?"
A: [Searches Confluence docs, JIRA tickets, and GitHub code]
   "The authentication feature uses OAuth2.0 as documented in 
    Confluence page 'Auth Architecture'. JIRA ticket PROJ-123 
    tracks the implementation. The code is in src/auth/oauth.py 
    using the passport library..."

Q: "Which JIRA tickets are related to the payment module?"
A: [Cross-references JIRA and GitHub]
   "Found 3 tickets: PROJ-456 (Payment Gateway Integration), 
    PROJ-457 (Stripe API), PROJ-458 (Payment UI). These relate 
    to files in src/payment/ directory..."

Q: "Show me all planned features in JIRA that don't have code yet"
A: [Analyzes JIRA vs GitHub]
   "Found 5 planned features without implementation:
    1. PROJ-789: Two-factor authentication
    2. PROJ-790: Social login
    ..."
```

## Use Case 2: Onboarding New Team Members

### Scenario
Help new developers understand the codebase and documentation.

### Steps
1. Connect GitHub (main repo)
2. Connect Confluence (onboarding docs)
3. Connect Google Drive (team resources)

### Example Questions
```
Q: "How do I set up the development environment?"
A: [Searches README.md, Confluence, Drive docs]

Q: "What's the architecture of the backend?"
A: [Finds architecture diagrams and code structure]

Q: "Where are the API endpoints defined?"
A: [Points to specific files and documentation]
```

## Use Case 3: Bug Investigation

### Scenario
Investigate a bug by looking at code, issues, and documentation.

### Steps
1. Connect GitHub
2. Connect JIRA
3. Upload error logs (File Reader)

### Example Questions
```
Q: "What could cause error 'Connection timeout' in the logs?"
A: [Analyzes logs, code, and related JIRA tickets]

Q: "Has this bug been reported before?"
A: [Searches JIRA history]

Q: "Show me the code that handles database connections"
A: [Finds relevant code files]
```

## Use Case 4: Documentation Sync Check

### Scenario
Ensure documentation matches actual implementation.

### Steps
1. Connect Confluence (API docs)
2. Connect GitHub (API code)

### Example Questions
```
Q: "Are all API endpoints documented in Confluence?"
A: [Compares code endpoints vs documentation]

Q: "Which documented features are not implemented yet?"
A: [Cross-references docs and code]
```

## Use Case 5: Sprint Planning

### Scenario
Plan sprint by understanding current state and dependencies.

### Steps
1. Connect JIRA (backlog)
2. Connect GitHub (current code)
3. Connect Confluence (technical specs)

### Example Questions
```
Q: "What's the complexity of implementing feature X?"
A: [Analyzes specs, existing code, and dependencies]

Q: "Which tickets depend on the auth refactor?"
A: [Finds related tickets and code]

Q: "What technical debt exists in the payment module?"
A: [Analyzes code and JIRA technical debt tickets]
```

## Tips for Best Results

### 1. Be Specific
❌ "Tell me about the project"
✅ "What authentication methods are implemented in the codebase?"

### 2. Reference Sources
❌ "How does it work?"
✅ "How does the payment flow work according to Confluence and the GitHub implementation?"

### 3. Ask Cross-Platform Questions
✅ "Which JIRA tickets relate to files in src/api/?"
✅ "Is the feature in JIRA-123 documented in Confluence?"
✅ "Show me code examples for the feature described in [Confluence page]"

### 4. Use Follow-up Questions
```
Q1: "What is the user authentication flow?"
Q2: "Show me the code for step 2 of that flow"
Q3: "Are there any open JIRA tickets about authentication bugs?"
```

### 5. Request Comparisons
✅ "Compare the documented API in Confluence with actual endpoints in GitHub"
✅ "What's different between the planned feature in JIRA and current implementation?"
