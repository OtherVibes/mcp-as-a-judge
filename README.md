# ⚖️ MCP as a Judge

<div align="left">
  <img src="assets/mcp-as-a-judge.png" alt="MCP as a Judge Logo" width="200">
</div>

> **MCP as a Judge acts as a validation layer between AI coding assistants and LLMs, helping ensure safer and higher-quality code.
*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

[![CI](https://github.com/hepivax/mcp-as-a-judge/workflows/CI/badge.svg)](https://github.com/hepivax/mcp-as-a-judge/actions/workflows/ci.yml)
[![Release](https://github.com/hepivax/mcp-as-a-judge/workflows/Release/badge.svg)](https://github.com/hepivax/mcp-as-a-judge/actions/workflows/release.yml)
[![PyPI version](https://img.shields.io/pypi/v/mcp-as-a-judge.svg)](https://pypi.org/project/mcp-as-a-judge/)



**MCP as a Judge** is a revolutionary Model Context Protocol (MCP) server that **transforms the developer-AI collaboration experience**. It acts as an intelligent gatekeeper for software development, preventing bad coding practices by using AI-powered evaluation and involving users in critical decisions when requirements are unclear or obstacles arise.

> **⚖️ Concept**: This project extends the **LLM-as-a-Judge** paradigm to software engineering workflows, where AI models evaluate and guide development decisions rather than just generating code.

## ⚖️ **Main Purpose: Improve Developer-AI Interface**

**The core mission is to enhance the interface between developers and AI coding assistants** by:

- 🛡️ **Preventing AI from making poor decisions** through intelligent evaluation
- 🤝 **Involving humans in critical choices** instead of AI making assumptions
- 🔍 **Enforcing research and best practices** before implementation
- ⚖️ **Creating a collaborative AI-human workflow** for better software quality

## **Vibe Coding doesn't have to be frustrating**

### **What It Enforces:**

- ✅ **Deep research** of existing solutions and best practices
- ✅ **Generic, reusable solutions** instead of quick fixes
- ✅ **User requirements alignment** in all implementations
- ✅ **Comprehensive planning** before coding begins
- ✅ **User involvement** in all critical decisions
- ✅ **Intelligent AI-human collaboration** with clear boundaries and responsibilities

## 🛠️ **Features**

### **🔍 Intelligent Code Evaluation**

- **LLM-powered analysis** using MCP [sampling](https://modelcontextprotocol.io/docs/learn/client-concepts#sampling) capability
- **Software engineering best practices** enforcement
- **Security vulnerability detection**
- **Performance and maintainability assessment**

### **📋 Comprehensive Planning Review**

- **Architecture validation** against industry standards
- **Research depth analysis** to prevent reinventing solutions
- **Requirements alignment** verification
- **Implementation approach evaluation**

### **🤝 User-Driven Decision Making**

- **Obstacle resolution** through user involvement via MCP [elicitation](https://modelcontextprotocol.io/docs/learn/client-concepts#elicitation)
- **Requirements clarification** when requests are unclear
- **No hidden fallbacks** - transparent decision making
- **Interactive problem solving** with real-time user input

### **🛠️ List of Tools**

| Tool Name | Description |
|-----------|-------------|
| **`build_workflow`** | Smart workflow analysis and tool recommendation |
| **`judge_coding_plan`** | Comprehensive plan evaluation with requirements alignment |
| **`judge_code_change`** | Code review with security and quality checks |
| **`raise_obstacle`** | User involvement when blockers arise |
| **`raise_missing_requirements`** | Clarification of unclear requests |

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

**✅ Recommended Setup:** GitHub Copilot in Visual Studio Code for the best MCP as a Judge experience.

**⚠️ LLM API Key Requirement:**
- **GitHub Copilot + VS Code**: ✅ **No API key needed** - Uses built-in MCP sampling
- **All Other Assistants**: ⚠️ **Requires LLM API key** - Limited MCP sampling support

Configure an LLM API key (OpenAI, Anthropic, Google, etc.) as described in the [LLM API Configuration](#-llm-api-configuration-optional) section.


#### **💡 Recommendations**

- **Large Context Window Models**: 1M+ token size models are strongly preferred for optimal performance
- Models with larger context windows provide better code analysis and more comprehensive judgments



## 🔧 **Visual Studio Code Configuration**

Configure **MCP as a Judge** in Visual Studio Code with GitHub Copilot:

### **Method 1: Using Docker (Recommended)**

1. **Configure MCP Settings:**

   Add this to your Visual Studio Code MCP configuration file:

   ```json
   {
     "mcpServers": {
       "mcp-as-a-judge": {
         "command": "docker",
         "args": ["run", "--rm", "-i", "--pull=always", "ghcr.io/hepivax/mcp-as-a-judge:latest"],
         "env": {
           "LLM_API_KEY": "your-openai-api-key-here",
           "LLM_MODEL_NAME": "gpt-4o-mini"
         }
       }
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
   docker pull ghcr.io/hepivax/mcp-as-a-judge:latest
   ```

### **Method 2: Using uv**

1. **Install the package:**

   ```bash
   uv tool install mcp-as-a-judge
   ```

2. **Configure MCP Settings:**

   The MCP server will be automatically detected by Visual Studio Code.

   **📝 Notes:**
   - **No additional configuration needed for GitHub Copilot + VS Code** (has built-in MCP sampling)
   - LLM_API_KEY is optional and can be set via environment variable if needed

3. **To update to the latest version:**

   ```bash
   # Update MCP as a Judge to the latest version
   uv tool upgrade mcp-as-a-judge
   ```

## 🔑 **LLM API Configuration (Optional)**

For AI assistants without full MCP sampling support (Cursor, Claude Code, Augment, Qodo), you can configure an LLM API key as a fallback. This ensures MCP as a Judge works even when the client doesn't support MCP sampling.

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

### **🎯 Model Selection Rationale**

All default models are optimized for **coding and reasoning tasks** with emphasis on speed:

- **⚡ Speed Optimized**: GPT-4.1 for fast elicitation and real-time interactions
- **🧠 Reasoning-Focused**: Claude Sonnet 4, Gemini 2.5 Pro with built-in thinking
- **⚡ Speed + Quality**: DeepSeek R1 on Groq/OpenRouter for fast reasoning
- **🎨 Multimodal**: Pixtral Large combines Mistral Large 2 with vision capabilities
- **🚀 Coding-Specialized**: Grok Code Fast 1 designed specifically for agentic coding
- **🏢 Enterprise**: AWS Bedrock and Vertex AI provide enterprise-grade access

### **⚙️ Coding-Optimized Configuration**

**Temperature: 0.1** (Low for deterministic, precise code generation)
- Ensures consistent, reliable code suggestions
- Reduces randomness for better debugging and maintenance
- Optimized for technical accuracy over creativity



### **🔑 When Do You Need an LLM API Key?**

| Coding Assistant | API Key Required? | Reason |
|------------------|-------------------|---------|
| **GitHub Copilot + VS Code** | ❌ **No** | Full MCP sampling support built-in |
| **Claude Code** | ✅ **Yes** | Limited MCP sampling support |
| **Cursor** | ✅ **Yes** | Limited MCP sampling support |
| **Augment** | ✅ **Yes** | Limited MCP sampling support |
| **Qodo** | ✅ **Yes** | Limited MCP sampling support |

**💡 Recommendation**: Use GitHub Copilot + VS Code for the best experience without needing API keys.

**🔍 Why Some Assistants Need API Keys:**
- **MCP Sampling**: GitHub Copilot supports advanced MCP sampling for dynamic prompts
- **Fallback Required**: Other assistants use LLM APIs when MCP sampling is unavailable
- **Future-Proof**: As more assistants add MCP sampling support, API keys become optional

### **Configuration Steps**

1. **Restart your MCP client** to pick up the environment variables.

### **How It Works**

- **Primary**: MCP as a Judge always tries MCP sampling first (when available)
- **Fallback**: If MCP sampling fails or isn't available, it uses your configured LLM API
- **Automatic**: No configuration needed - the system detects your API key and selects the appropriate provider
- **Privacy**: Your API key is only used when MCP sampling is not available

### **Client-Specific Setup**

#### **Cursor**

1. **Open Cursor Settings:**
   - Go to `File` → `Preferences` → `Cursor Settings`
   - Navigate to the `MCP` tab
   - Click `+ Add` to add a new MCP server

2. **Add MCP Server Configuration:**
   ```json
   {
     "mcpServers": {
       "mcp-as-a-judge": {
         "command": "uv",
         "args": ["tool", "run", "mcp-as-a-judge"],
         "env": {
           "LLM_API_KEY": "your-openai-api-key-here",
           "LLM_MODEL_NAME": "gpt-4.1"
         }
       }
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
     "mcpServers": {
       "mcp-as-a-judge": {
         "command": "uv",
         "args": ["tool", "run", "mcp-as-a-judge"],
         "env": {
           "LLM_API_KEY": "your-anthropic-api-key-here",
           "LLM_MODEL_NAME": "claude-3-5-haiku"
         }
       }
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
  "mcpServers": {
    "mcp-as-a-judge": {
      "command": "uv",
      "args": ["tool", "run", "mcp-as-a-judge"],
      "env": {
        "LLM_API_KEY": "your-openai-api-key-here",
        "LLM_MODEL_NAME": "gpt-4o-mini"
      }
     }
   }
   ```

**📝 Configuration Options:**
- **LLM_API_KEY**: Required for most MCP clients (except GitHub Copilot + VS Code)
- **LLM_MODEL_NAME**: Optional custom model (see [Supported LLM Providers](#supported-llm-providers) for defaults)




## 📖 **How It Works**

Once MCP as a Judge is configured with your AI coding assistant, it automatically guides the AI through a structured software engineering workflow. The system operates transparently in the background, ensuring every development task follows best practices.

### **🔄 Automatic Workflow Enforcement**

**1. Intelligent Workflow Guidance**

- When you make any development request, the AI assistant automatically calls `build_workflow`
- This tool uses AI analysis to determine which validation steps are required for your specific task
- Provides smart recommendations on which tools to use next and in what order
- No manual intervention needed - the workflow starts automatically with intelligent guidance

**2. Planning & Design Phase**

- For any implementation task, the AI assistant must first help you create:
  - **Detailed coding plan** - Step-by-step implementation approach
  - **System design** - Architecture, components, and technical decisions
  - **Research findings** - Analysis of existing solutions and best practices
- Once complete, `judge_coding_plan` automatically evaluates the plan using MCP Sampling
- **AI-powered evaluation** checks for design quality, security, research thoroughness, and requirements alignment

**3. Code Implementation Review**

- After any code is written or modified, `judge_code_change` is automatically triggered
- **Mandatory code review** happens immediately after file creation/modification
- Uses MCP Sampling to evaluate code quality, security vulnerabilities, and best practices
- Ensures every code change meets professional standards

### **🤝 User Involvement When Needed**

**Obstacle Resolution**

- When the AI assistant encounters blockers or conflicting requirements, `raise_obstacle` automatically engages you
- Uses MCP Elicitation to present options and get your decision
- No hidden fallbacks - you're always involved in critical decisions

**Requirements Clarification**

- If your request lacks sufficient detail, `raise_missing_requirements` automatically asks for clarification
- Uses MCP Elicitation to gather specific missing information
- Ensures implementation matches your actual needs

### **🎯 What to Expect**

- **Automatic guidance** - No need to explicitly ask the AI coding assistant to call tools
- **Comprehensive planning** - Every implementation starts with proper design and research
- **Quality enforcement** - All code changes are automatically reviewed against industry standards
- **User-driven decisions** - You're involved whenever your original request cannot be satisfied
- **Professional standards** - Consistent application of software engineering best practices

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
- Set environment variables like `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.

### **🛡️ Your Privacy Matters**

- The server runs **locally** on your machine
- **No data collection** - your code and conversations stay private
- **No external API calls** - everything happens within your local environment
- Complete control over your development workflow and sensitive information

## 🤝 **Contributing**

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### **Development Setup**

```bash
# Clone the repository
git clone https://github.com/hepivax/mcp-as-a-judge.git
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

### **Release Process**

This project uses automated semantic versioning:

1. **Commit with conventional commits**: `feat:`, `fix:`, `docs:`, etc.
2. **Push to main**: Semantic release will automatically create tags and releases
3. **Manual releases**: Create a tag `v1.2.3` and push to trigger release workflow

```bash
# Example conventional commits
git commit -m "feat: add new validation rule for async functions"
git commit -m "fix: resolve memory leak in server startup"
git commit -m "docs: update installation instructions"
```

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- [LiteLLM](https://github.com/BerriAI/litellm) for unified LLM API integration

---

**🚨 Ready to revolutionize your development workflow? Install MCP as a Judge today!**
