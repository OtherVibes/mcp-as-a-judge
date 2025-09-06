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
- **🎯 Informed LLM Decisions**: LLM tools enriched with historical context

## Vector in memory is not in use for semantic search, it can be added later

### **🎯 Memory Usage Strategy**

**Tools that USE context enrichment (LLM-based analysis):**
- **`build_workflow`** - LLM needs conversation history to understand project evolution
- **`judge_coding_plan`** - LLM needs history to make consistent judgments with past decisions
- **`judge_code_change`** - LLM needs context to maintain consistency across code reviews

**Tools that DON'T need context enrichment (User interaction):**
- **`raise_obstacle`** - User already has full context from their session
- **`raise_missing_requirements`** - User knows what they're working on

**All tools SAVE to history:**
- Every tool result gets saved for future LLM context enrichment

### **📋 Memory Strategy Summary**

| Tool | Context Enrichment | Reason | Save to History |
|------|-------------------|--------|-----------------|
| **`build_workflow`** | ✅ YES | LLM needs project evolution context | ✅ YES |
| **`judge_coding_plan`** | ✅ YES | LLM needs consistency with past decisions | ✅ YES |
| **`judge_code_change`** | ✅ YES | LLM needs consistency across code reviews | ✅ YES |
| **`raise_obstacle`** | ❌ NO | User has full session context already | ✅ YES |
| **`raise_missing_requirements`** | ❌ NO | User knows their own requirements | ✅ YES |

**Key Insight:** LLM tools need historical context to make informed decisions, while user interaction tools rely on the user's inherent knowledge of their session context.

### **SQLite Database with Conversation History**

#### **📊 Database Configuration Options**

The Judge MCP supports multiple database backends via URL configuration:

```json
{
  "database": {
    "url": "sqlite://:memory:",                                    // SQLite in-memory (default)
    "url": "sqlite:///path/to/conversations.db",                  // SQLite persistent file
    "url": "postgresql://user:password@localhost:5432/mcp_judge", // PostgreSQL
    "url": "mysql://user:password@localhost:3306/mcp_judge",      // MySQL
    "max_context_records": 20,
    "context_enrichment_count": 5,
    "record_retention_days": 1
  }
}
```

#### **📊 Conversation History Features**
```
Purpose: Store conversation history and provide context enrichment for LLM sampling
Features: LRU cleanup, session isolation, context loading for tool enrichment, time-based cleanup

CONVERSATION HISTORY WORKFLOW:
✅ Before LLM tools: Load last X conversation records for context enrichment
✅ Before user tools: No context enrichment needed (user has full context)
✅ After ALL tools: Save tool interaction (input, output) for future LLM use
✅ LRU cleanup: Automatically remove oldest records when max limit exceeded
✅ Session isolation: Each session maintains separate conversation history

Storage Schema:
CREATE TABLE conversation_history (
    id TEXT PRIMARY KEY,                    -- UUID for each conversation
    session_id TEXT NOT NULL,               -- Session identifier from AI agent
    source TEXT NOT NULL,                   -- Tool name (e.g., "judge_coding_plan")
    input TEXT NOT NULL,                    -- Tool input as JSON string
    output TEXT NOT NULL,                   -- Tool output as JSON string
    timestamp TEXT NOT NULL                 -- ISO format datetime
);

Configuration:
{
  "database": {
    "url": "sqlite://:memory:",             -- Database connection URL
    "max_context_records": 20,              -- Total records to keep per session (LRU)
    "context_enrichment_count": 5,          -- Records to load for LLM context
    "record_retention_days": 1              -- Days to keep records before cleanup
  }
}

Example Record:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "session-abc",
  "source": "judge_coding_plan",
  "input": "{\"plan\": \"REST API\", \"user_requirements\": \"...\"}",
  "output": "{\"approved\": true, \"feedback\": \"Good plan\"}",
  "timestamp": "2024-01-15T10:30:00.000Z"
}

API Operations:
• save_conversation(session_id, source, input_data, output) → Save tool interaction
• get_session_conversations(session_id, limit) → Get recent conversations for session
• clear_session(session_id) → Remove all conversations for session (TEST-ONLY)
• get_stats() → Get database statistics (TEST-ONLY)
```

#### **🔧 Custom Database Providers**

The Judge MCP supports extending the database system with custom providers using the `register_provider` method. This allows you to add support for new database backends without modifying the core codebase.

##### **Creating a Custom Provider**

1. **Implement the Interface**: Create a class that extends `ConversationHistoryDB`:

```python
from mcp_as_a_judge.db.interface import ConversationHistoryDB, ConversationRecord
from datetime import datetime

class RedisProvider(ConversationHistoryDB):
    """Redis-based conversation history provider."""

    def __init__(self, max_context_records: int = 20, retention_days: int = 1, url: str = "") -> None:
        """Initialize Redis connection."""
        import redis
        self._redis = redis.from_url(url)
        self._max_context_records = max_context_records
        self._retention_days = retention_days

    async def save_conversation(self, session_id: str, source: str, input_data: str, output: str) -> str:
        """Save conversation to Redis."""
        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "session_id": session_id,
            "source": source,
            "input": input_data,
            "output": output,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Store in Redis with session-based keys
        key = f"conversation:{session_id}:{record_id}"
        self._redis.hset(key, mapping=record)
        self._redis.expire(key, self._retention_days * 24 * 3600)  # TTL in seconds

        return record_id

    async def get_session_conversations(self, session_id: str, limit: int | None = None) -> list[ConversationRecord]:
        """Retrieve conversations from Redis."""
        pattern = f"conversation:{session_id}:*"
        keys = self._redis.keys(pattern)

        records = []
        for key in keys:
            data = self._redis.hgetall(key)
            if data:
                records.append(ConversationRecord(
                    id=data[b'id'].decode(),
                    session_id=data[b'session_id'].decode(),
                    source=data[b'source'].decode(),
                    input=data[b'input'].decode(),
                    output=data[b'output'].decode(),
                    timestamp=datetime.fromisoformat(data[b'timestamp'].decode())
                ))

        # Sort by timestamp and apply limit
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit] if limit else records
```

2. **Register the Provider**: Add your custom provider to the factory:

```python
from mcp_as_a_judge.db.factory import DatabaseFactory
from your_module.providers import RedisProvider

# Register the custom provider
DatabaseFactory.register_provider("redis", RedisProvider)
```

3. **Configure the URL**: Update your configuration to use the new provider:

```json
{
  "database": {
    "url": "redis://localhost:6379/0",
    "max_context_records": 20,
    "record_retention_days": 1
  }
}
```

##### **Provider Registration Examples**

**Plugin System Integration:**
```python
# In your plugin's __init__.py
from mcp_as_a_judge.db.factory import DatabaseFactory
from .providers import MongoDBProvider, CassandraProvider

def register_providers():
    """Register all providers from this plugin."""
    DatabaseFactory.register_provider("mongodb", MongoDBProvider)
    DatabaseFactory.register_provider("cassandra", CassandraProvider)

# Auto-register when plugin is imported
register_providers()
```

**Conditional Provider Loading:**
```python
# In application startup
from mcp_as_a_judge.config import Config
from mcp_as_a_judge.db.factory import DatabaseFactory

config = Config()

# Only register PostgreSQL if the driver is available
try:
    import psycopg2
    from .providers.postgresql import PostgreSQLProvider
    DatabaseFactory.register_provider("postgresql", PostgreSQLProvider)
except ImportError:
    print("PostgreSQL driver not available, skipping registration")

# Only register if explicitly enabled
if config.database.enable_experimental_providers:
    from .providers.experimental import ExperimentalProvider
    DatabaseFactory.register_provider("experimental", ExperimentalProvider)
```

**Testing with Mock Providers:**
```python
# In test setup
from mcp_as_a_judge.db.factory import DatabaseFactory
from unittest.mock import MagicMock

class MockDatabaseProvider:
    def __init__(self, **kwargs):
        self.conversations = []

    async def save_conversation(self, session_id, source, input_data, output):
        # Mock implementation
        return "mock-id"

    async def get_session_conversations(self, session_id, limit=None):
        # Return mock data
        return []

# Register for testing
DatabaseFactory.register_provider("mock", MockDatabaseProvider)

# Use in tests with mock:// URL
config.database.url = "mock://test"
```

##### **URL Scheme Detection**

The factory automatically detects the provider from the URL scheme. For custom providers, you may need to extend the `get_database_provider_from_url` function in `config.py`:

```python
def get_database_provider_from_url(url: str) -> str:
    # ... existing logic ...

    # Custom provider detection
    elif url_lower.startswith("redis://"):
        return "redis"
    elif url_lower.startswith("mongodb://"):
        return "mongodb"
    elif url_lower.startswith("cassandra://"):
        return "cassandra"

    # ... rest of function ...
```

This extensible architecture allows the Judge MCP to support any database backend while maintaining a consistent interface and configuration system.

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
│  │ BEFORE LLM Tool Execution: Context Enrichment                      │   │
│  │ ┌─────────────────────────────────────────────────────────────┐     │   │
│  │ │ LLM Tools (build_workflow, judge_*, etc.):                 │     │   │
│  │ │ 1. Load last 5 conversation records for session            │     │   │
│  │ │ 2. Format as context for LLM enrichment                    │     │   │
│  │ │ 3. Append to original tool prompt                          │     │   │
│  │ │                                                             │     │   │
│  │ │ User Tools (raise_obstacle, raise_missing_requirements):    │     │   │
│  │ │ • Skip context enrichment (user has full context)          │     │   │
│  │ └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                     │   │
│  │ DURING Tool Execution: LLM Sampling vs User Interaction            │   │
│  │ ┌─────────────────────────────────────────────────────────────┐     │   │
│  │ │ LLM Tools: Original prompt + conversation history context   │     │   │
│  │ │ • LLM makes informed decision based on past interactions   │     │   │
│  │ │                                                             │     │   │
│  │ │ User Tools: Direct user interaction                        │     │   │
│  │ │ • Present options/questions directly to user               │     │   │
│  │ │ • No LLM analysis needed (user decides)                    │     │   │
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
        ├─── 📚 Load Conversation History Context (LLM TOOL - needs context)
        │    ├─── 📊 SQLite: get_recent_conversations(session_id, count=5) → return last 5 conversation records
        │    └─── 📝 Format: Load full conversation records and format for LLM context enrichment
        │
        ├─── 🧠 MCP Sampling (Ask AI for workflow guidance - which of Judge MCP tools to call next)
        │    ├─── AI Prompt: "What workflow steps needed for REST API task?"
        │    ├─── Context: "## Previous Conversation History\n### 1. judge_coding_plan...\n### 2. judge_code_change..."
        │    └─── AI Response: "This needs planning phase - recommend judge_coding_plan"
        │
        └─── 💾 Save Tool Interaction & Return Guidance (ALL TOOLS save to history)
             ├─── Save: ConversationRecord(source="build_workflow", input="{...}", output="{...}")
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
        ├─── 📚 Load Conversation History Context (LLM TOOL - needs context)
        │    ├─── 📊 SQLite: get_recent_conversations(session_id, count=5) → return conversation records
        │    └─── 📝 Format: "## Previous Conversation History\n### 1. build_workflow: next_tool=judge_coding_plan\n### 2. judge_code_change: rejected - security issues"
        │
        ├─── 🧠 MCP Sampling (Ask AI to evaluate plan quality)
        │    ├─── AI Prompt: "Evaluate this plan for quality and security"
        │    ├─── Context: Previous conversation history + current plan details
        │    └─── AI Response: "Plan APPROVED - addresses previous security concerns"
        │
        └─── 💾 Save Tool Interaction & Return Result (ALL TOOLS save to history)
             ├─── Save: ConversationRecord(source="judge_coding_plan", input="{plan, design, research...}", output="{approved: true, feedback...}")
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
        ├─── 📚 Load Conversation History Context (LLM TOOL - needs context)
        │    ├─── 📊 SQLite: get_recent_conversations(session_id, count=5) → return conversation records
        │    └─── 📝 Format: "Previous decisions: Approved bcrypt, rejected raw SQL concatenation"
        │
        ├─── 🧠 MCP Sampling (Ask AI to review code quality of new file users.py)
        │    ├─── AI Prompt: "Review this code for security vulnerabilities"
        │    ├─── Context: "User concerned about SQL injection, prefers parameterized queries"
        │    └─── AI Response: "Code APPROVED - proper parameterized queries used"
        │
        └─── 💾 Save Review & Return Result (ALL TOOLS save to history)
             ├─── Save: ConversationRecord(source="judge_code_change", input="{...}", output="{...}")
             └─── Response: approved=true, guidance="Continue workflow"

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

1. **⚖️ Judge:** raise_obstacle() (USER TOOL - no context enrichment needed)
   - **Obstacle:** "Database schema conflicts with API design"
   - **Options:** ["Modify schema", "Adjust API", "Create migration"]
   - **No LLM context loading** - user has full session context

2. **🤝 MCP Elicitation:** Present options to user

3. **👤 Developer:** Makes decision → "Create migration"

4. **💾 Save interaction:** ConversationRecord(source="raise_obstacle", input="{...}", output="Create migration")

5. **🤖 AI Assistant:** Continues with user's choice

### **Scenario B: Requirements Unclear**

**LLM Detects missing information and suggest to invoke judge mcp raise_missing_requirements() with some options**

1. **⚖️ Judge:** raise_missing_requirements() (USER TOOL - no context enrichment needed)
   - **Gaps:** ["Authentication method", "Rate limiting", "Data validation rules"]
   - **Questions:** ["Should we use JWT?", "What's the rate limit?", "Required fields?"]
   - **No LLM context loading** - user knows their requirements

2. **🤝 MCP Elicitation:** Ask user for clarifications

3. **👤 Developer:** Provides missing requirements

4. **💾 Save interaction:** ConversationRecord(source="raise_missing_requirements", input="{...}", output="{...}")

5. **🤖 AI Assistant:** Continues with clarified requirements

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

