# 🤖 AI Agent with MCP as a Judge - Complete Workflow Diagram

## 📋 **System Architecture Overview**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           🤖 AI Coding Assistant                                │
│                        (Cursor / Claude / VS Code)                             │
│                    ┌─── Orchestrates all MCP servers ───┐                      │
└────────────────────┼─────────────────────────────────────┼──────────────────────┘
                     │                                     │
                     ▼                                     ▼
    ┌─────────────────────────┐                     ┌─────────────────────────┐
    │    ⚖️ MCP as a Judge     │                     │    🛠️ Other MCP Servers │
    │  (Quality Validator +   │                     │                         │
    │   Context Memory)       │                     │  📁 File System MCP     │
    │                         │                     │  🌐 Web Search MCP      │
    │ • build_workflow        │                     │  🔄 Git MCP             │
    │ • judge_coding_plan     │                     │  🗄️ Database MCP        │
    │ • judge_code_change     │                     │  🔌 API MCP             │
    │ • raise_obstacle        │                     │  🧪 Testing MCP         │
    │ • raise_missing_req     │                     └─────────────────────────┘
    │                         │
    │ 🧠 Built-in Memory:     │
    │ 📊 SQLite In-Memory DB  │
    │ • Conversation history  │
    │ • Context enrichment    │
    │ • LRU cleanup          │
    │ • Session management   │
    └─────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────┐
    │     👤 Developer        │
    │   (User Involvement)    │
    └─────────────────────────┘
```

## 🎯 **Why MCP As A Judge?**

**AI agent feedback loop can be implemented in 2 main approaches:**

***AI agent (reviewer) which validate the response that was created by another AI agent**

***MCP server (this project) which does not change AI workflow, instead it's added as a seamless plugin (tool) in the existing AI workflow**

## MCP Judge server use MCP concepts:

## 🧠 **MCP Sampling**

**MCP Sampling** = MCP server ask (using prompt) an AI assistant's LLM or any other another LLM which of the Judge mcp tool needs to be invoke next (brain remain LLM)

## 🤝 **MCP Elicitation**

**MCP Elicitation** = LLM ask Judge MCP server to asks the **human user** interactive questions and waits for their response

```
⚖️ LLM I need more info --> Judge MCP Server: "I need the user to make a decision"
        │
        ├─── Creates interactive form/dialog with options
        ├─── Sends to user via ctx.elicit(message="Choose option A, B, or C", schema=...)
        ├─── 👤 User sees dialog in their AI assistant interface
        ├─── 👤 User selects option and provides input
        └─── Judge gets user's decision and continues workflow
```

**Key Point**: Judge MCP pauses the workflow and waits for human input when decisions are needed!

## ⚖️ **MCP Sampling vs MCP Elicitation - Key Differences**

| Feature              | 🧠 MCP Sampling | 🤝 MCP Elicitation |
|----------------------|----------------|-------------------|
| **Who responds?**    | 🤖 AI Model | 👤 Human User |
| **Purpose**          | Get AI analysis/evaluation | Get user decisions/clarifications |
| **When used?**       | Quality validation, technical analysis | Obstacle resolution, missing requirements |
| **Response time**    | Instant (milliseconds) | Waits for user (minutes/hours) |
| **Example question** | "Is this code secure?" | "Which approach do you prefer?" |
| **Code call**        | `ctx.session.create_message()` | `ctx.elicit()` |
| **Response format**  | Text/JSON analysis | Structured form data |
| **Workflow impact**  | Continues immediately | Pauses until user responds |


**Example Workflow:**
```
1. 🧠 Judge MCP uses MCP Sampling: "Is this code secure?" → AI: "Has SQL injection vulnerability" --> AI calls judge MCP raise_obstacle()
2. 🤝 MCP Elicitation: "How should we fix it?" → User: "Use parameterized queries"
3. 🧠 MCP Sampling: "Is the fix correct?" → AI: "Yes, vulnerability resolved"
```

## 🧠 **Judge MCP Built-in Memory - Context & Learning**

### **Why Memory is Essential for Judge MCP**

The Judge MCP has **built-in conversation history** to make **better, context-aware decisions**:

- **🔍 Context Continuity**: Remember previous tool interactions and decisions
- **📈 Session Learning**: Build context from conversation history within session
- **🚫 Avoid Repetition**: Reference previous decisions and feedback
- **🎯 Informed Decisions**: Each tool call enriched with historical context

### **SQLite In-Memory Database with Conversation History**

#### **📊 SQLite In-Memory Conversation History**
```
Purpose: Store conversation history and provide context enrichment for LLM sampling
Features: LRU cleanup, session isolation, context loading for tool enrichment

CONVERSATION HISTORY WORKFLOW:
✅ Before each tool: Load last X conversation records for context enrichment
✅ After each tool: Save tool interaction (input, output, context IDs)
✅ LRU cleanup: Automatically remove oldest records when max limit exceeded
✅ Session isolation: Each session maintains separate conversation history

Storage Schema (SQLite In-Memory):
CREATE TABLE conversation_history (
    id TEXT PRIMARY KEY,                    -- UUID for each conversation
    session_id TEXT NOT NULL,               -- Session identifier from AI agent
    source TEXT NOT NULL,                   -- Tool name (e.g., "judge_coding_plan")
    input TEXT NOT NULL,                    -- Tool input as JSON string
    context TEXT NOT NULL,                  -- JSON array of conversation IDs used for enrichment
    output TEXT NOT NULL,                   -- Tool output as JSON string
    timestamp TEXT NOT NULL                 -- ISO format datetime
);

Configuration:
{
  "database": {
    "provider": "in_memory",
    "max_context_records": 20,              -- Total records to keep per session (LRU)
    "context_enrichment_count": 5           -- Records to load for LLM context
  }
}

Example Record:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "session-abc",
  "source": "judge_coding_plan",
  "input": "{\"plan\": \"REST API\", \"user_requirements\": \"...\"}",
  "context": "[\"uuid-123\", \"uuid-789\"]",
  "output": "{\"approved\": true, \"feedback\": \"Good plan\"}",
  "timestamp": "2024-01-15T10:30:00.000Z"
}

API Operations:
• save_conversation(session_id, source, input_data, context, output) → Save tool interaction
• get_session_conversations(session_id, limit) → Get recent conversations for session
• get_recent_conversations(session_id, count) → Get conversation IDs for context
• clear_session(session_id) → Remove all conversations for session
```

### **🏗️ Judge MCP Conversation History Architecture**

```
User Input: "Build REST API with S3 file storage"
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           🤖 AI Agent Orchestrator                          │
│ 1. Receives user input                                                      │
│ 2. Calls Judge MCP build_workflow() with session_id                         │
│ 3. Orchestrates other MCP servers based on Judge guidance                   │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ⚖️ Judge MCP Server                                  │
│                                                                             │
│  📊 SQLite In-Memory Database (conversation_history table)                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ BEFORE Tool Execution: Context Enrichment                          │   │
│  │ ┌─────────────────────────────────────────────────────────────┐     │   │
│  │ │ 1. Load last 5 conversation records for session            │     │   │
│  │ │ 2. Format as context for LLM enrichment                    │     │   │
│  │ │ 3. Append to original tool prompt                          │     │   │
│  │ └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                     │   │
│  │ DURING Tool Execution: LLM Sampling                                │   │
│  │ ┌─────────────────────────────────────────────────────────────┐     │   │
│  │ │ • Original prompt + conversation history context            │     │   │
│  │ │ • LLM makes informed decision based on past interactions   │     │   │
│  │ └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                     │   │
│  │ AFTER Tool Execution: Save Conversation Record                     │   │
│  │ ┌─────────────────────────────────────────────────────────────┐     │   │
│  │ │ ConversationRecord {                                        │     │   │
│  │ │   id: "uuid-123",                                           │     │   │
│  │ │   session_id: "session-abc",                                │     │   │
│  │ │   source: "judge_coding_plan",                              │     │   │
│  │ │   input: "{\"plan\": \"...\", \"requirements\": \"...\"}",  │     │   │
│  │ │   context: ["uuid-456", "uuid-789"],  // Previous conv IDs │     │   │
│  │ │   output: "{\"approved\": true, \"feedback\": \"...\"}",    │     │   │
│  │ │   timestamp: "2024-01-15T10:30:00Z"                        │     │   │
│  │ │ }                                                           │     │   │
│  │ └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                     │   │
│  │ LRU Cleanup: If session > max_context_records (20)                 │   │
│  │ ┌─────────────────────────────────────────────────────────────┐     │   │
│  │ │ • Automatically remove oldest conversation records          │     │   │
│  │ │ • Keep only most recent 20 records per session             │     │   │
│  │ └─────────────────────────────────────────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### **⚙️ Conversation History Configuration**

#### **🗄️ LRU Cleanup & Session Management**

**Problem:** Without limits, conversation history can grow indefinitely causing:
- 💾 Memory bloat (SQLite in-memory database consuming all RAM)
- 🐌 Performance degradation (Context loading getting slower)
- 🧠 Context overload (Too much history confusing LLM decisions)

**Solution:** Automatic LRU cleanup per session:

```json
{
  "database": {
    "provider": "in_memory",
    "max_context_records": 20,        // Total records to keep per session
    "context_enrichment_count": 5     // Records to load for LLM context
  }
}
```

#### **🎯 Recommended Configuration Settings**

| Environment | max_context_records | context_enrichment_count | Use Case |
|-------------|-------------------|-------------------------|----------|
| **Development** | 10 | 3 | Fast testing, minimal memory |
| **Production** | 20 | 5 | Balanced performance/memory |
| **High-Volume** | 50 | 10 | Power users, more context |
| **Constrained** | 5 | 2 | Limited resources |

## 🔄 **Complete Development Workflow with Memory**

### **Phase 1: Initial Request & Workflow Guidance**

```
👤 Developer: "Build a REST API for user management"
        │
        ▼
🤖 AI Assistant: Receives request → Its coding task so AI assistant call Judge MCP build_workflow()
        │
        ▼
⚖️ Judge MCP: build_workflow(task_description)
        │
        ├─── 📚 Load Conversation History Context
        │    ├─── 📊 SQLite: get_recent_conversations(session_id, count=5) → return last 5 conversation IDs
        │    └─── 📝 Format: Load full conversation records and format for LLM context enrichment
        │
        ├─── 🧠 MCP Sampling (Ask AI for workflow guidance - which of Judge MCP tools to call next)
        │    ├─── AI Prompt: "What workflow steps needed for REST API task?"
        │    ├─── Context: "## Previous Conversation History\n### 1. judge_coding_plan...\n### 2. judge_code_change..."
        │    └─── AI Response: "This needs planning phase - recommend judge_coding_plan"
        │
        └─── 💾 Save Tool Interaction & Return Guidance
             ├─── Save: ConversationRecord(source="build_workflow", input="{...}", output="{...}", context=[...])
             └─── Response: next_tool="judge_coding_plan", guidance="Start planning..."

🎯 KEY POINT: LLM used in this flow to answer which mcp judge tool to call next according to the context:

   Task: "Build new REST API" 
   → AI Analysis: "This needs planning first"
   → Result: next_tool = "judge_coding_plan"
   
   Task: "Fix this bug in existing code"
   → AI Analysis: "This is code modification, review the change"  
   → Result: next_tool = "judge_code_change"
   
   Task: "I want to add authentication but not sure which type"
   → AI Analysis: "Requirements are unclear"
   → Result: next_tool = "raise_missing_requirements"
   
   Task: "Database is down, can't continue development"
   → AI Analysis: "This is a blocker/obstacle"
   → Result: next_tool = "raise_obstacle"
```

### **Phase 2: AI Agent Orchestrates Research (Judge MCP Not Involved)**

```
🤖 AI Assistant: Receives Judge guidance like need to create plan→ AI CHOOSES which MCP servers to use for research task
        │
        ├─── 🌐 Web Search MCP: "REST API best practices"
        │    └─── Returns: Documentation, tutorials, security guides
        │
        ├─── 📁 File System MCP: "existing_patterns.py"
        │    └─── Returns: Current codebase patterns
        │
        └─── 🗄️ Database MCP: get_schema_info()
             └─── Returns: Current database structure

🎯 IMPORTANT: AI Assistant orchestrates - Judge MCP doesn't choose these servers!
```

### **Phase 3: Planning & Design Validation**

```
🤖 AI Assistant: Creates comprehensive plan using research from multiple MCP servers with Judge mcp server
   Phase 2 output is fed into Judge MCP server which will use LLM to evaluate the plan
        │
        ▼
⚖️ Judge MCP: judge_coding_plan(plan, design, research, user_requirements)
        │
        ├─── 📚 Load Conversation History Context
        │    ├─── 📊 SQLite: get_recent_conversations(session_id, count=5) → return conversation IDs
        │    └─── 📝 Format: "## Previous Conversation History\n### 1. build_workflow: next_tool=judge_coding_plan\n### 2. judge_code_change: rejected - security issues"
        │
        ├─── 🧠 MCP Sampling (Ask AI to evaluate plan quality)
        │    ├─── AI Prompt: "Evaluate this plan for quality and security"
        │    ├─── Context: Previous conversation history + current plan details
        │    └─── AI Response: "Plan APPROVED - addresses previous security concerns"
        │
        └─── 💾 Save Tool Interaction & Return Result
             ├─── Save: ConversationRecord(source="judge_coding_plan", input="{plan, design, research...}", output="{approved: true, feedback...}", context=[...])
             └─── Response: approved=true, guidance="Proceed to implementation" OR Reject

📋 **Plan Evaluation Results:**
┌─────────────────────────────────────────────────────────────────┐
│  ✅ APPROVED                    │  ❌ REJECTED                   │
│  • Plan meets standards         │  • Missing security measures   │
│  • Research is thorough         │  • Insufficient error handling │
│  • Architecture is sound        │  • Needs more research         │
│  → Proceed to implementation    │  → Return to planning phase    │
└─────────────────────────────────────────────────────────────────┘
```

### **Phase 4: Implementation with Continuous Review**

```
Now plan approved start to implement and once agent finished to code change ??? , judge mcp will review the results by send LLM to vaerify change is accordingn to standards
🤖 AI Assistant: Begins implementation using File System MCP
        │
        ├─── 📁 File System MCP: create_file("api/users.py", code_content)
        │
        ▼
⚖️ Judge MCP: judge_code_change(code, user_requirements, file_path) -- Code review cycles
        │
        ├─── 📚 Load Memory Context
        │    ├─── 🔍 Vector: "SQL injection security" → User had issues before
        │    └─── 📊 Rational: "Approved bcrypt, rejected raw SQL concatenation"
        │
        ├─── 🧠 MCP Sampling (Ask AI to review code quality of new file users.py)
        │    ├─── AI Prompt: "Review this code for security vulnerabilities"
        │    ├─── Context: "User concerned about SQL injection, prefers parameterized queries"
        │    └─── AI Response: "Code APPROVED - proper parameterized queries used"
        │
        └─── 💾 Save Review & Return Result
             └─── Response: approved=true, guidance="Continue workflow"
             └─── On next change ??? there will be another judge validation cycle 

🔍 **Code Review Results:**
┌─────────────────────────────────────────────────────────────────┐
│  ✅ APPROVED                    │  ❌ NEEDS IMPROVEMENT          │
│  • Code follows best practices  │  • Security vulnerabilities    │
│  • Proper error handling        │  • Performance issues          │
│  • Good documentation           │  • Missing validations         │
│  → Continue workflow            │  → Fix issues & re-review      │
└─────────────────────────────────────────────────────────────────┘
```



## 🤝 **User Involvement Scenarios**

### **Scenario A: Obstacle Encountered**

**LLM Detects conflicting requirements and suggest to invoke judge mcp raise_obstacle() with some options**

1. **⚖️ Judge:** raise_obstacle()
   - **Obstacle:** "Database schema conflicts with API design"
   - **Options:** ["Modify schema", "Adjust API", "Create migration"]

2. **🤝 MCP Elicitation:** Present options to user

3. **👤 Developer:** Makes decision → "Create migration"

4. **🤖 AI Assistant:** Continues with user's choice

### **Scenario B: Requirements Unclear**

**LLM Detects missing informatio and suggest to invoke judge mcp raise_missing_requirements() with some options**

1. **⚖️ Judge:** raise_missing_requirements()
   - **Gaps:** ["Authentication method", "Rate limiting", "Data validation rules"]
   - **Questions:** ["Should we use JWT?", "What's the rate limit?", "Required fields?"]

2. **🤝 MCP Elicitation:** Ask user for clarifications

3. **👤 Developer:** Provides missing requirements

4. **🤖 AI Assistant:** Continues with clarified requirements

## 🧠 **Judge MCP Features**

**📋 judge_coding_plan():**
- Creates evaluation prompt from Jinja2 template
- ctx.session.create_message(messages=prompts, max_tokens=1000)
- AI model analyzes: plan quality, security, best practices
- Returns structured JudgeResponse

**🔍 judge_code_change():**
- Creates code review prompt from Jinja2 template
- ctx.session.create_message(messages=prompts, max_tokens=1000)
- AI model analyzes: code quality, vulnerabilities, maintainability
- Returns structured JudgeResponse

**🚨 raise_obstacle():**
- Creates interactive dialog with options
- ctx.elicit(message="🚨 OBSTACLE: Choose approach...", schema=dynamic_form)
- 👤 User sees form in AI assistant interface
- 👤 User selects option and provides context
- Returns user's decision to continue workflow

**🔍 raise_missing_requirements():**
- Creates clarification form with questions
- ctx.elicit(message="🔍 CLARIFICATION NEEDED...", schema=requirements_form)
- 👤 User fills out missing requirements and priorities
- 👤 User submits completed form
- Returns clarified requirements to continue workflow

## 🗄️ **Conversation History Patterns & Usage Guide**

### **📊 SQLite Conversation History Operations**

#### **Pattern 1: Recent Entries (Any Source)**
```python
# Use Case: Get overall recent activity
recent_entries = memory.get_last_n_entries(session_id="user_123", n=5)

# Returns (most recent first):
[
  {"content": "build_workflow result: next_tool=judge_coding_plan", "source": "judge_mcp"},
  {"content": "User chose JWT over sessions", "source": "judge_mcp"},
  {"content": "Applied context: User's JWT preference", "source": "judge_mcp"},
  {"content": "AI evaluation: Recommend planning workflow", "source": "judge_mcp"},
  {"content": "judge_coding_plan called with plan='...'", "source": "judge_mcp"}
]
```

#### **Pattern 2: Recent Judge Decisions Only** // can be any source (mcp tool)
```python
# Use Case: Get recent judge-specific decisions
judge_decisions = memory.get_last_n_entries(session_id="user_123", n=3, source="judge_mcp")

# Returns (most recent first):
[
  {"content": "judge_coding_plan result: APPROVED", "source": "judge_mcp"},
  {"content": "judge_code_change result: REJECTED - SQL injection", "source": "judge_mcp"},
  {"content": "build_workflow result: next_tool=judge_coding_plan", "source": "judge_mcp"}
]
```

### **🔍 Vector Memory Query Patterns (Complex Semantic)**

```python
# Use Case: Find user's security-related patterns
security_patterns = memory.query_vector(
    query="security vulnerability SQL injection validation sanitization",
    top_k=3,
    session_id="user_123"
)

# Returns:
[
  {"content": "User concerned about SQL injection vulnerabilities", "score": 0.91},
  {"content": "User implements input validation and sanitization", "score": 0.87},
  {"content": "User adds rate limiting for API security", "score": 0.83}
]
```

### **🎯 Memory Usage Decision Matrix**

| Scenario | Memory Type | Query Pattern | Example |
|----------|-------------|---------------|---------|
| **Recent decisions** | 📊 Relational | `get_last_n_entries(session_id, n)` | "What did I decide recently?" |
| **Recent judge actions** | 📊 Relational | `get_last_n_entries(session_id, n, "judge_mcp")` | "Last 3 judge decisions" |
| **Security patterns** | 🔍 Vector | `query_vector("security vulnerability", top_k)` | "User's security practices" |


#### **Every Judge MCP Tool Saves Complete Execution:**

```python
# COMPLETE TOOL EXECUTION (Input + Output in one atomic operation)
save_entry(
    session_id=session_id,
    source="judge_mcp",
    tool_name="judge_coding_plan",  # build_workflow, judge_code_change, raise_obstacle, raise_missing_requirements
    input={
        "user_requirements": "Build REST API for user management",
        "plan": "1. Create user model with validation...",
        "design": "Architecture: Express.js + PostgreSQL...",
        "research": "Found libraries: bcrypt, joi, express-validator...",
        "research_urls": ["https://...", "https://...", "https://..."]
    },
    output={
        "approved": true,
        "required_improvements": [],
        "feedback": "Plan follows all best practices. Good security considerations..."
    },
    timestamp=1690000000
)
```

## 📋 **Real Examples: Sampling vs Elicitation in Action**

### **Example 1: Code Security Review**

```
🧠 MCP Sampling Example:
⚖️ Judge: judge_code_change(code="SELECT * FROM users WHERE id = " + user_id)
        │
        ├─── Creates prompt: "Analyze this SQL code for security vulnerabilities"
        ├─── ctx.session.create_message(messages=[security_analysis_prompt])
        ├─── 🤖 AI Model: "CRITICAL: SQL injection vulnerability detected on line 1..."
        └─── Returns: JudgeResponse(approved=false, required_improvements=["Fix SQL injection"])
```

### **Example 2: User Decision on Fix Approach**

```
🤝 MCP Elicitation Example:
⚖️ Judge: raise_obstacle(
   problem="SQL injection found",
   options=["Use ORM", "Parameterized queries", "Input validation"]
)
        │
        ├─── Creates dialog: "🚨 OBSTACLE: How should we fix the SQL injection?"
        ├─── ctx.elicit(message="Choose approach:", schema=choice_form)
        ├─── 👤 User sees options in AI assistant interface
        ├─── 👤 User selects: "Use parameterized queries + input validation"
        └─── Returns: "Proceed with parameterized queries and input validation approach"
```

### **Example 3: Requirements Clarification**

```
🤝 MCP Elicitation Example:
⚖️ Judge: raise_missing_requirements(gaps=["Authentication method", "Session duration"])
        │
        ├─── Creates form: "🔍 CLARIFICATION: Please specify authentication details"
        ├─── ctx.elicit(message="Missing requirements:", schema=requirements_form)
        ├─── 👤 User fills form:
        │    • Authentication: "JWT tokens"
        │    • Session duration: "24 hours"
        │    • Priority: "High"
        └─── Returns: "Use JWT tokens with 24-hour expiration (High priority)"
```

## ⚠️ **Error Handling & Fallbacks**

### **When MCP Sampling Fails**

```
⚖️ Judge MCP: Attempts AI evaluation
        │
        ├─── 🧠 MCP Sampling: FAILED
        │
        ▼
⚖️ Judge: Provides fallback guidance
   • Default recommendations
   • Basic validation rules
   • Conservative approach
```

### **When User is Unavailable**

```
⚖️ Judge MCP: Needs user input
        │
        ├─── 🤝 MCP Elicitation: User not responding
        │
        ▼
⚖️ Judge: Queue workflow
   • Pause implementation
   • Save current state
   • Wait for user availability
```

## 🎯 **Key Benefits of This Architecture**

### **1. Structured Workflow Enforcement**
- ✅ Mandatory planning phase
- ✅ Continuous code review
- ✅ Quality gates at each step

### **2. Multi-MCP Coordination**
- ⚖️ Judge MCP orchestrates the workflow
- 🛠️ Specialized MCPs handle specific tasks
- 🤖 AI Assistant coordinates all interactions

### **3. User-Driven Decision Making**
- 🤝 No hidden AI assumptions
- 🤝 Transparent obstacle resolution
- 🤝 Interactive requirement gathering

### **4. Professional Development Standards**
- 📋 Comprehensive planning required
- 🔍 Thorough research enforced
- 🛡️ Security and quality validation
- 📚 Best practices compliance

---

**Result**: A professional, structured development workflow where AI assistants follow software engineering best practices, conduct proper research, validate quality at each step, and involve users in critical decisions.
