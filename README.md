# ⚖️ MCP as a Judge

> **Prevent bad coding practices with AI-powered evaluation and user-driven decision making**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

[![CI](https://github.com/hepivax/mcp-as-a-judge/workflows/CI/badge.svg)](https://github.com/hepivax/mcp-as-a-judge/actions/workflows/ci.yml)
[![Release](https://github.com/hepivax/mcp-as-a-judge/workflows/Release/badge.svg)](https://github.com/hepivax/mcp-as-a-judge/actions/workflows/release.yml)
[![PyPI version](https://badge.fury.io/py/mcp-as-a-judge.svg)](https://badge.fury.io/py/mcp-as-a-judge)

[![codecov](https://codecov.io/gh/hepivax/mcp-as-a-judge/branch/main/graph/badge.svg)](https://codecov.io/gh/hepivax/mcp-as-a-judge)

**MCP as a Judge** is a revolutionary Model Context Protocol (MCP) server that **transforms the developer-AI collaboration experience**. It acts as an intelligent gatekeeper for software development, preventing bad coding practices by using AI-powered evaluation and involving users in critical decisions when requirements are unclear or obstacles arise.

> **⚖️ Concept**: This project extends the **LLM-as-a-Judge** paradigm to software engineering workflows, where AI models evaluate and guide development decisions rather than just generating code.

## ⚖️ **Main Purpose: Improve Developer-AI Interface**

**The core mission is to enhance the interface between developers and AI coding assistants** by:

- 🛡️ **Preventing AI from making poor decisions** through intelligent evaluation
- 🤝 **Involving humans in critical choices** instead of AI making assumptions
- 🔍 **Enforcing research and best practices** before implementation
- ⚖️ **Creating a collaborative AI-human workflow** for better software quality

## 😌 **Vibe Coding doesn't have to be frustrating**

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

### **⚖️ Five Powerful Judge Tools**

1. **`get_workflow_guidance`** - Smart workflow analysis and tool recommendation
2. **`judge_coding_plan`** - Comprehensive plan evaluation with requirements alignment
3. **`judge_code_change`** - Code review with security and quality checks
4. **`raise_obstacle`** - User involvement when blockers arise
5. **`elicit_missing_requirements`** - Clarification of unclear requests

## 🚀 **Quick Start**

### **Requirements & Recommendations**

#### **⚠️ Critical Requirements**

MCP as a Judge is heavily dependent on **MCP Sampling** and **MCP Elicitation** features for its core functionality:

- **[MCP Sampling](https://modelcontextprotocol.io/docs/learn/client-concepts#sampling)** - Required for AI-powered code evaluation and judgment
- **[MCP Elicitation](https://modelcontextprotocol.io/docs/learn/client-concepts#elicitation)** - Required for interactive user decision prompts

#### **🔧 Supported AI Assistants**

Currently, **GitHub Copilot in VS Code** is the only AI assistant that fully supports these MCP features. Other coding assistants and other versions of GitHub Copilot are not supported at this time.

#### **📋 Technical Prerequisites**

- Python 3.12+ (latest secure version)
- GitHub Copilot with MCP support enabled

#### **💡 Recommendations**

- **Large Context Window Models**: 1M+ token size models are strongly preferred for optimal performance
- Models with larger context windows provide better code analysis and more comprehensive judgments

> **Note**: MCP servers communicate via stdio (standard input/output), not HTTP ports. No network configuration is needed.

### **Installation**

#### **Method 1: Using uv (Recommended)**

```bash
# Install uv if you don't have it
pip install uv

# Install from PyPI
uv add mcp-as-a-judge

# Run the server
mcp-as-a-judge
```

#### **Method 2: Using pip (Alternative)**

```bash
# Install from PyPI
pip install mcp-as-a-judge

# Run the server
mcp-as-a-judge
```

#### **Method 3: From Source (Development)**

```bash
# Clone the repository for development
git clone https://github.com/hepivax/mcp-as-a-judge.git
cd mcp-as-a-judge

# Install with uv
uv sync --all-extras --dev

# Run the server
uv run mcp-as-a-judge
```

## 🔧 **VS Code Configuration**

Configure MCP as a Judge in VS Code with GitHub Copilot:

1. **Install the package:**

   ```bash
   uv add mcp-as-a-judge
   ```

2. **Configure VS Code MCP settings:**

   Add this to your VS Code MCP configuration file:

   ```json
   {
     "servers": {
       "mcp-as-a-judge": {
         "command": "uv",
         "args": ["run", "mcp-as-a-judge"]
       }
     }
   }
   ```

### **📍 VS Code MCP Configuration Location**

The MCP configuration file is typically located at:

- **Windows**: `%APPDATA%\Code\User\globalStorage\github.copilot-chat\mcp.json`
- **macOS**: `~/Library/Application Support/Code/User/globalStorage/github.copilot-chat/mcp.json`
- **Linux**: `~/.config/Code/User/globalStorage/github.copilot-chat/mcp.json`

### **🔄 Restart VS Code**

After adding the configuration, restart VS Code to load the MCP server.

#### **Environment Variables**

**Available Environment Variables:**

```bash
# Transport Configuration
TRANSPORT=sse              # Options: "stdio" or "sse"
HOST=0.0.0.0              # Server host (SSE only)
PORT=8050                 # Server port (SSE only)

# Logging
LOG_LEVEL=INFO            # Options: DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json           # Options: json, text

# Development
DEBUG=false               # Enable debug mode
DEVELOPMENT_MODE=false    # Enable development features

# Performance
MAX_CONCURRENT_REQUESTS=10  # Maximum concurrent requests
REQUEST_TIMEOUT=30          # Request timeout in seconds

# Security
CORS_ENABLED=false        # Enable CORS (production: false)
CORS_ORIGINS=*            # CORS allowed origins
```

## 📖 **How It Works**

Once MCP as a Judge is configured in VS Code with GitHub Copilot, it automatically guides your AI assistant through a structured software engineering workflow. The system operates transparently in the background, ensuring every development task follows best practices.

### **🔄 Automatic Workflow Enforcement**

**1. Intelligent Workflow Guidance**

- When you make any development request, the AI assistant automatically calls `get_workflow_guidance`
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

- If your request lacks sufficient detail, `elicit_missing_requirements` automatically asks for clarification
- Uses MCP Elicitation to gather specific missing information
- Ensures implementation matches your actual needs

### **🎯 What to Expect**

- **Automatic guidance** - No need to explicitly ask the AI coding assistant to call tools
- **Comprehensive planning** - Every implementation starts with proper design and research
- **Quality enforcement** - All code changes are automatically reviewed against industry standards
- **User-driven decisions** - You're involved whenever your original request cannot be satisfied
- **Professional standards** - Consistent application of software engineering best practices

## 🔒 **Privacy & API Key Free**

### **🔑 No LLM API Key Required**

- All judgments are performed using **MCP Sampling** capability
- No need to configure or pay for external LLM API services
- Works directly with your MCP-compatible client's existing AI model

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
- The amazing MCP community for inspiration and best practices
- All developers who will benefit from better coding practices

---

**🚨 Ready to revolutionize your development workflow? Install MCP as a Judge today!**
