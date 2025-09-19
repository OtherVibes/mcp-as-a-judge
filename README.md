# MCP as a Judge ⚖️

mcp-name: io.github.OtherVibes/mcp-as-a-judge

<div align="left">
  <img src="assets/mcp-as-a-judge.png" alt="MCP as a Judge Logo" width="200">
</div>

> MCP as a Judge acts as a validation layer between AI coding assistants and LLMs, helping ensure safer and higher-quality code.


[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/license/mit/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

[![CI](https://github.com/OtherVibes/mcp-as-a-judge/workflows/CI/badge.svg)](https://github.com/OtherVibes/mcp-as-a-judge/actions/workflows/ci.yml)
[![Release](https://github.com/OtherVibes/mcp-as-a-judge/workflows/Release/badge.svg)](https://github.com/OtherVibes/mcp-as-a-judge/actions/workflows/release.yml)
[![PyPI version](https://img.shields.io/pypi/v/mcp-as-a-judge.svg)](https://pypi.org/project/mcp-as-a-judge/)



**MCP as a Judge** is a **behavioral MCP** that strengthens AI coding assistants by requiring explicit LLM evaluations for:
- Research, system design, and planning
- Code changes, testing, and task-completion verification

It enforces evidence-based research, reuse over reinvention, and human-in-the-loop decisions.

> If your IDE has rules/agents (Copilot, Cursor, Claude Code), keep using them—this Judge adds enforceable approval gates on plan, code diffs, and tests.


## Key problems with AI coding assistants and LLMs
- Treat LLM output as ground truth; skip research and use outdated information
- Reinvent the wheel instead of reusing libraries and existing code
- Cut corners: code below engineering standards and weak tests
- Make unilateral decisions when requirements are ambiguous or plans change
- Security blind spots: missing input validation, injection risks/attack vectors, least‑privilege violations, and weak defensive programming


## **Vibe coding doesn’t have to be frustrating**

### What it enforces
- Evidence‑based research and reuse (best practices, libraries, existing code)
- Plan‑first delivery aligned to user requirements
- Human‑in‑the‑loop decisions for ambiguity and blockers
- Quality gates on code and tests (security, performance, maintainability)

### Key capabilities
- Intelligent code evaluation via MCP [sampling](https://modelcontextprotocol.io/docs/learn/client-concepts#sampling); enforces software‑engineering standards and flags security/performance/maintainability risks
- Comprehensive plan/design review: validates architecture, research depth, requirements fit, and implementation approach
- User‑driven decisions via MCP [elicitation](https://modelcontextprotocol.io/docs/learn/client-concepts#elicitation): clarifies requirements, resolves obstacles, and keeps choices transparent
- Security validation in system design and code changes



### Tools and how they help
| Tool | What it solves |
|------|-----------------|
| `set_coding_task` | Creates/updates task metadata; classifies task_size; returns next-step workflow guidance |
| `get_current_coding_task` | Recovers the latest task_id and metadata to resume work safely |
| `judge_coding_plan` | Validates plan/design; requires library selection and internal reuse maps; flags risks |
| `judge_code_change` | Reviews unified Git diffs for correctness, reuse, security, and code quality |
| `judge_testing_implementation` | Validates tests using real runner output and optional coverage |
| `judge_coding_task_completion` | Final gate ensuring plan, code, and tests approvals before completion |
| `raise_missing_requirements` | Elicits missing details and decisions to unblock progress |
| `raise_obstacle` | Engages the user on trade‑offs, constraints, and enforced changes |

## 🔄 **Collaborative Refinement Workflow**

MCP as a Judge implements a sophisticated collaborative workflow that ensures high-quality outcomes through iterative user-LLM collaboration:

## 🔄 Enhanced Collaborative Workflow

### **Phase 1: 🧠 Enhanced Brainstorming**
```
📋 get_enhanced_user_feedback
├── Requirements gathering + clarifications
├── Documentation & reference requests
├── Success criteria definition
├── Environment & deployment context
└── Testing strategy preferences
```

### **Phase 2: 📋 Comprehensive Plan Creation**
```
🔬 create_implementation_plan
├── Technical research & analysis
├── Architecture & design patterns
├── Test strategy & coverage requirements
├── Implementation scope & milestones
└── Risk assessment & mitigation
```

### **Phase 3: 🔄 Dual Approval Loop**
```
👤 User Review → get_user_approve_requirement
├── ✅ Approved → LLM Technical Validation
└── ❌ Rejected → Back to Brainstorming

🤖 LLM Review → judge_coding_plan
├── ✅ Approved → Dual Approval Achieved
└── ❌ Rejected → update_plan_with_llm_feedback
    └── Creates Plan B → User Re-Review
        ├── ✅ Approved → LLM Re-Validation
        └── ❌ Rejected → Back to Brainstorming
```

### **Phase 4: 🚀 Enhanced Implementation**
```
🧹 Clean History (delete brainstorming records)
    ↓
🏗️ judge_code_change (Architecture + Security Review)
    ↓
👤 User Code Review (Optional validation step)
    ↓
🧪 judge_testing_implementation (Tests + Coverage)
    ↓
📚 Documentation Review (Optional documentation check)
    ↓
✅ judge_coding_task_completion (Final quality gate)
    ↓
🎉 Task Complete
```

### **🔑 Key Quality Enhancements**
- **📋 Comprehensive Requirements**: Documentation, success criteria, environment context
- **🧪 Test-First Planning**: Test strategy integrated from planning phase
- **🔄 Iterative Refinement**: Multiple approval loops ensure quality
- **👤 User Involvement**: Optional code review for critical changes
- **📚 Documentation Focus**: Optional documentation validation
- **🛡️ Multi-Layer Validation**: Architecture, security, testing, and completion gates

### **🎯 Key Workflow Principles**

**Phase 1: Collaborative Requirements Refinement**
- **Iterative Brainstorming**: Multiple cycles until requirements are crystal clear
- **LLM Plan Creation**: Research-backed, best-practice implementation plans
- **User Control**: User has final say on approach and requirements
- **Quality Focus**: No plan proceeds without user satisfaction

**Phase 2: Dual Approval System (CRITICAL)**
- **User Approves Plan A**: Initial plan approval by user
- **LLM Technical Review**: LLM validates Plan A for technical soundness
- **Plan Modification**: If LLM rejects, creates Plan B with improvements
- **User Re-Approval Required**: User MUST approve Plan B (different from Plan A!)
- **Iterative Refinement**: Continues until BOTH user + LLM approve SAME plan
- **True Collaboration**: No automatic plan changes without user consent

**Phase 3: Implementation Excellence**
- **Dual Approval Guarantee**: Implementation uses plan approved by BOTH parties
- **History Cleanup**: Removes brainstorming records after dual approval
- **Focused Context**: Implementation uses only the final dual-approved plan
- **Quality Assurance**: Multiple validation layers ensure excellent outcomes

## 🚀 **Quick Start**

### **Requirements & Recommendations**

#### **MCP Client Prerequisites**

MCP as a Judge is heavily dependent on **MCP Sampling** and **MCP Elicitation** features for its core functionality:

- **[MCP Sampling](https://modelcontextprotocol.io/docs/learn/client-concepts#sampling)** - Required for AI-powered code evaluation and judgment
- **[MCP Elicitation](https://modelcontextprotocol.io/docs/learn/client-concepts#elicitation)** - Required for interactive user decision prompts

#### **System Prerequisites**

- **Docker Desktop** / **Python 3.13+** - Required for running the MCP server

#### **Supported AI Assistants**

| AI Assistant | Platform | MCP Support | Status | Notes |
|---------------|----------|-------------|---------|-------|
| **GitHub Copilot** | Visual Studio Code | ✅ Full | **Recommended** | Complete MCP integration with sampling and elicitation |
| **Claude Code** | - | ⚠️ Partial | Requires LLM API key | [Sampling Support feature request](https://github.com/anthropics/claude-code/issues/1785)<br>[Elicitation Support feature request](https://github.com/anthropics/claude-code/issues/2799) |
| **Cursor** | - | ⚠️ Partial | Requires LLM API key | MCP support available, but sampling/elicitation limited |
| **Augment** | - | ⚠️ Partial | Requires LLM API key | MCP support available, but sampling/elicitation limited |
| **Qodo** | - | ⚠️ Partial | Requires LLM API key | MCP support available, but sampling/elicitation limited |

**✅ Recommended setup:** GitHub Copilot + VS Code — full MCP sampling; no API key needed.

**⚠️ Critical:** For assistants without full MCP sampling (Cursor, Claude Code, Augment, Qodo), you MUST set `LLM_API_KEY`. Without it, the server cannot evaluate plans or code. See [LLM API Configuration](#-llm-api-configuration-optional).

**💡 Tip:** Prefer large context models (≥ 1M tokens) for better analysis and judgments.

### If the MCP server isn’t auto‑used
For troubleshooting, visit the [FAQs section](#faq).

## 🔧 **MCP Configuration**

Configure **MCP as a Judge** in your MCP-enabled client:

### **Method 1: Using Docker (Recommended)**

#### One‑click install for VS Code (MCP)

[![Install for MCP as a Judge](https://img.shields.io/badge/VS_Code-Install_for_MCP_as_a_Judge-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=mcp-as-a-judge&inputs=%5B%5D&config=%7B%22command%22%3A%22docker%22%2C%22args%22%3A%5B%22run%22%2C%22-i%22%2C%22--rm%22%2C%22--pull%3Dalways%22%2C%22ghcr.io%2Fothervibes%2Fmcp-as-a-judge%3Alatest%22%5D%7D)



Notes:
- VS Code controls the sampling model; select it via “MCP: List Servers → mcp-as-a-judge → Configure Model Access”.


1. **Configure MCP Settings:**

   Add this to your MCP client configuration file:

   ```json
   {
     "command": "docker",
     "args": ["run", "--rm", "-i", "--pull=always", "ghcr.io/othervibes/mcp-as-a-judge:latest"],
     "env": {
       "LLM_API_KEY": "your-openai-api-key-here",
       "LLM_MODEL_NAME": "gpt-4o-mini"
     }
   }
   ```

   **📝 Configuration Options (All Optional):**
   - **LLM_API_KEY**: Optional for GitHub Copilot + VS Code (has built-in MCP sampling)
   - **LLM_MODEL_NAME**: Optional custom model (see [Supported LLM Providers](#supported-llm-providers) for defaults)
   - The `--pull=always` flag ensures you always get the latest version automatically

   Then manually update when needed:

   ```bash
   # Pull the latest version
   docker pull ghcr.io/othervibes/mcp-as-a-judge:latest
   ```

### **Method 2: Using uv**

1. **Install the package:**

   ```bash
   uv tool install mcp-as-a-judge
   ```

2. **Configure MCP Settings:**

   The MCP server may be automatically detected by your MCP‑enabled client.

   **📝 Notes:**
   - **No additional configuration needed for GitHub Copilot + VS Code** (has built-in MCP sampling)
   - LLM_API_KEY is optional and can be set via environment variable if needed

3. **To update to the latest version:**

   ```bash
   # Update MCP as a Judge to the latest version
   uv tool upgrade mcp-as-a-judge
   ```
### Select a sampling model in VS Code
- Open Command Palette (Cmd/Ctrl+Shift+P) → “MCP: List Servers”
- Select the configured server “mcp-as-a-judge”
- Choose “Configure Model Access”
- Check your preferred model(s) to enable sampling



## 🔑 **LLM API Configuration (Optional)**

For [AI assistants without full MCP sampling support](#supported-ai-assistants) you can configure an LLM API key as a fallback. This ensures MCP as a Judge works even when the client doesn't support MCP sampling.

- Set `LLM_API_KEY` (unified key). Vendor is auto-detected; optionally set `LLM_MODEL_NAME` to override the default.

### **Supported LLM Providers**

| Rank | Provider | API Key Format | Default Model | Notes |
|------|----------|----------------|---------------|-------|
| **1** | **OpenAI** | `sk-...` | `gpt-4.1` | Fast and reliable model optimized for speed |
| **2** | **Anthropic** | `sk-ant-...` | `claude-sonnet-4-20250514` | High-performance with exceptional reasoning |
| **3** | **Google** | `AIza...` | `gemini-2.5-pro` | Most advanced model with built-in thinking |
| **4** | **Azure OpenAI** | `[a-f0-9]{32}` | `gpt-4.1` | Same as OpenAI but via Azure |
| **5** | **AWS Bedrock** | AWS credentials | `anthropic.claude-sonnet-4-20250514-v1:0` | Aligned with Anthropic |
| **6** | **Vertex AI** | Service Account JSON | `gemini-2.5-pro` | Enterprise Gemini via Google Cloud |
| **7** | **Groq** | `gsk_...` | `deepseek-r1` | Best reasoning model with speed advantage |
| **8** | **OpenRouter** | `sk-or-...` | `deepseek/deepseek-r1` | Best reasoning model available |
| **9** | **xAI** | `xai-...` | `grok-code-fast-1` | Latest coding-focused model (Aug 2025) |
| **10** | **Mistral** | `[a-f0-9]{64}` | `pixtral-large` | Most advanced model (124B params) |



### **Client-Specific Setup**

#### **Cursor**

1. **Open Cursor Settings:**
   - Go to `File` → `Preferences` → `Cursor Settings`
   - Navigate to the `MCP` tab
   - Click `+ Add` to add a new MCP server

2. **Add MCP Server Configuration:**
   ```json
   {
     "command": "uv",
     "args": ["tool", "run", "mcp-as-a-judge"],
     "env": {
       "LLM_API_KEY": "your-openai-api-key-here",
       "LLM_MODEL_NAME": "gpt-4.1"
     }
   }
   ```

   **📝 Configuration Options:**
   - **LLM_API_KEY**: Required for Cursor (limited MCP sampling)
   - **LLM_MODEL_NAME**: Optional custom model (see [Supported LLM Providers](#supported-llm-providers) for defaults)

#### **Claude Code**

1. **Add MCP Server via CLI:**
   ```bash
   # Set environment variables first (optional model override)
   export LLM_API_KEY="your_api_key_here"
   export LLM_MODEL_NAME="claude-3-5-haiku"  # Optional: faster/cheaper model

   # Add MCP server
   claude mcp add mcp-as-a-judge -- uv tool run mcp-as-a-judge
   ```

2. **Alternative: Manual Configuration:**
   - Create or edit `~/.config/claude-code/mcp_servers.json`
   ```json
   {
     "command": "uv",
     "args": ["tool", "run", "mcp-as-a-judge"],
     "env": {
       "LLM_API_KEY": "your-anthropic-api-key-here",
       "LLM_MODEL_NAME": "claude-3-5-haiku"
     }
   }
   ```

   **📝 Configuration Options:**
   - **LLM_API_KEY**: Required for Claude Code (limited MCP sampling)
   - **LLM_MODEL_NAME**: Optional custom model (see [Supported LLM Providers](#supported-llm-providers) for defaults)

#### **Other MCP Clients**

For other MCP-compatible clients, use the standard MCP server configuration:

```json
{
  "command": "uv",
  "args": ["tool", "run", "mcp-as-a-judge"],
  "env": {
    "LLM_API_KEY": "your-openai-api-key-here",
    "LLM_MODEL_NAME": "gpt-5"
  }
}
```

**📝 Configuration Options:**
- **LLM_API_KEY**: Required for most MCP clients (except GitHub Copilot + VS Code)
- **LLM_MODEL_NAME**: Optional custom model (see [Supported LLM Providers](#supported-llm-providers) for defaults)





## 🔒 **Privacy & Flexible AI Integration**

### **🔑 MCP Sampling (Preferred) + LLM API Key Fallback**

**Primary Mode: MCP Sampling**
- All judgments are performed using **MCP Sampling** capability
- No need to configure or pay for external LLM API services
- Works directly with your MCP-compatible client's existing AI model
- **Currently supported by:** GitHub Copilot + VS Code

**Fallback Mode: LLM API Key**
- When MCP sampling is not available, the server can use LLM API keys
- Supports multiple providers via LiteLLM: OpenAI, Anthropic, Google, Azure, Groq, Mistral, xAI
- Automatic vendor detection from API key patterns
- Default model selection per vendor when no model is specified


### **🛡️ Your Privacy Matters**

- The server runs **locally** on your machine
- **No data collection** - your code and conversations stay private
- **No external API calls when using MCP Sampling**. If you set `LLM_API_KEY` for fallback, the server will call your chosen LLM provider only to perform judgments (plan/code/test) with the evaluation content you provide.
- Complete control over your development workflow and sensitive information

## 🤝 **Contributing**

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### **Development Setup**

```bash
# Clone the repository
git clone https://github.com/OtherVibes/mcp-as-a-judge.git
cd mcp-as-a-judge

# Install dependencies with uv
uv sync --all-extras --dev

# Install pre-commit hooks
uv run pre-commit install

# Run tests
uv run pytest

# Run all checks
uv run pytest && uv run ruff check && uv run ruff format --check && uv run mypy src
```


## © Concepts and Methodology
© 2025 OtherVibes and Zvi Fried. The "MCP as a Judge" concept, the "behavioral MCP" approach, the staged workflow (plan → code → test → completion), tool taxonomy/descriptions, and prompt templates are original work developed in this repository.


## Prior Art and Attribution
While “LLM‑as‑a‑judge” is a broadly known idea, this repository defines the original “MCP as a Judge” behavioral MCP pattern by OtherVibes and Zvi Fried. It combines task‑centric workflow enforcement (plan → code → test → completion), explicit LLM‑based validations, and human‑in‑the‑loop elicitation, along with the prompt templates and tool taxonomy provided here. Please attribute as: “OtherVibes – MCP as a Judge (Zvi Fried)”.

## ❓ FAQ

### How is “MCP as a Judge” different from rules/subagents in IDE assistants (GitHub Copilot, Cursor, Claude Code)?
| Feature | IDE Rules | Subagents | MCP as a Judge |
|---------|-----------|-----------|----------------|
| Static behavior guidance | ✓ | ✓ | ✗ |
| Custom system prompts | ✓ | ✓ | ✓ |
| Project context integration | ✓ | ✓ | ✓ |
| Specialized task handling | ✗ | ✓ | ✓ |
| Active quality gates | ✗ | ✗ | ✓ |
| Evidence-based validation | ✗ | ✗ | ✓ |
| Approve/reject with feedback | ✗ | ✗ | ✓ |
| Workflow enforcement | ✗ | ✗ | ✓ |
| Cross-assistant compatibility | ✗ | ✗ | ✓ |
  - References: [GitHub Copilot Custom Instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions), [Cursor Rules](https://docs.cursor.com/en/context/@-symbols/@-cursor-rules), [Claude Code Subagents](https://docs.anthropic.com/en/docs/claude-code/sub-agents)

### How does the Judge workflow relate to the tasklist? Why do we need both?
- Tasklist = planning/organization: tracks tasks, priorities, and status. It doesn’t guarantee engineering quality or readiness.
- Judge workflow = quality gates: enforces approvals for plan/design, code diffs, tests, and final completion. It demands real evidence (e.g., unified Git diffs and raw test output) and returns structured approvals and required improvements.
- Together: Use the tasklist to organize work; use the Judge to decide when each stage is actually ready to proceed. The server also emits next_tool guidance to keep progress moving through the gates.

### If the Judge isn’t used automatically, how do I force it?
- In your prompt: "use mcp-as-a-judge" or "Evaluate plan/code/test using the MCP server mcp-as-a-judge".
- VS Code: Command Palette → "MCP: List Servers" → ensure "mcp-as-a-judge" is listed and enabled.
- Ensure the MCP server is running and, in your client, the judge tools are enabled/approved.

### How do I select models for sampling in VS Code?
- Open Command Palette (Cmd/Ctrl+Shift+P) → "MCP: List Servers"
- Select "mcp-as-a-judge" → "Configure Model Access"
- Check your preferred model(s) to enable sampling



## 📄 **License**

This project is licensed under the MIT License (see [LICENSE](LICENSE)).

## 🙏 **Acknowledgments**

- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- [LiteLLM](https://github.com/BerriAI/litellm) for unified LLM API integration

---

