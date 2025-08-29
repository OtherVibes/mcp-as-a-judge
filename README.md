# ⚖️ MCP as a Judge

> **Prevent bad coding practices with AI-powered evaluation and user-driven decision making**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://www.docker.com/)

[![CI](https://github.com/hepivax/mcp-as-a-judge/workflows/CI/badge.svg)](https://github.com/hepivax/mcp-as-a-judge/actions/workflows/ci.yml)
[![Release](https://github.com/hepivax/mcp-as-a-judge/workflows/Release/badge.svg)](https://github.com/hepivax/mcp-as-a-judge/actions/workflows/release.yml)
[![PyPI version](https://badge.fury.io/py/mcp-as-a-judge.svg)](https://badge.fury.io/py/mcp-as-a-judge)
[![Docker Image](https://ghcr-badge.egpl.dev/hepivax/mcp-as-a-judge/latest_tag?trim=major&label=latest)](https://github.com/hepivax/mcp-as-a-judge/pkgs/container/mcp-as-a-judge)
[![codecov](https://codecov.io/gh/hepivax/mcp-as-a-judge/branch/main/graph/badge.svg)](https://codecov.io/gh/hepivax/mcp-as-a-judge)

**MCP as a Judge** is a revolutionary Model Context Protocol (MCP) server that **transforms the developer-AI collaboration experience**. It acts as an intelligent gatekeeper for software development, preventing bad coding practices by using AI-powered evaluation and involving users in critical decisions when requirements are unclear or obstacles arise.

> **⚖️ Concept**: This project extends the **LLM-as-a-Judge** paradigm to software engineering workflows, where AI models evaluate and guide development decisions rather than just generating code.

## ⚖️ **Main Purpose: Improve Developer-AI Interface**

**The core mission is to enhance the interface between developers and AI coding assistants** by:

- 🛡️ **Preventing AI from making poor decisions** through intelligent evaluation
- 🤝 **Involving humans in critical choices** instead of AI making assumptions
- 🔍 **Enforcing research and best practices** before implementation
- ⚖️ **Creating a collaborative AI-human workflow** for better software quality

## 🚀 **This MCP Will Change Many Developers' Lives!**

### **What It Prevents:**

- ❌ Reinventing the wheel instead of using existing solutions
- ❌ Building workarounds instead of proper implementations
- ❌ Insufficient research leading to poor architectural decisions
- ❌ Misalignment between code and user requirements
- ❌ Deployment of problematic code without proper review

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

1. **`check_swe_compliance`** - Workflow guidance and best practices
2. **`judge_coding_plan`** - Comprehensive plan evaluation with requirements alignment
3. **`judge_code_change`** - Code review with security and quality checks
4. **`raise_obstacle`** - User involvement when blockers arise
5. **`elicit_missing_requirements`** - Clarification of unclear requests

## 🚀 **Quick Start**

### **Prerequisites**

- Python 3.12+ (latest secure version)
- MCP-compatible client that supports:
  - **[Sampling](https://modelcontextprotocol.io/docs/learn/client-concepts#sampling)** - Required for AI-powered code evaluation
  - **[Elicitation](https://modelcontextprotocol.io/docs/learn/client-concepts#elicitation)** - Required for user decision prompts
- Compatible clients: Claude Desktop, Cursor, etc.

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

#### **Method 2: Using Docker (Recommended for Production)**

**Quick Start with Docker:**

```bash
# Pull and run the latest image
docker run -it --name mcp-as-a-judge ghcr.io/hepivax/mcp-as-a-judge:latest
```

**Build from Source:**

```bash
# Clone the repository
git clone https://github.com/hepivax/mcp-as-a-judge.git
cd mcp-as-a-judge

# Build the Docker image
docker build -t mcp-as-a-judge:latest .

# Run with custom configuration
docker run -it \
  --name mcp-as-a-judge \
  -e LOG_LEVEL=INFO \
  --restart unless-stopped \
  mcp-as-a-judge:latest
```

**Using Docker Compose:**

```bash
# For production (uses pre-built image from GitHub Container Registry)
docker-compose --profile production up -d

# For development (builds from source)
git clone https://github.com/hepivax/mcp-as-a-judge.git
cd mcp-as-a-judge
docker-compose --profile development up
```

#### **Method 3: Using pip (Alternative)**

```bash
# Install from PyPI
pip install mcp-as-a-judge

# Run the server
mcp-as-a-judge
```

#### **Method 4: From Source (Development)**

```bash
# Clone the repository for development
git clone https://github.com/hepivax/mcp-as-a-judge.git
cd mcp-as-a-judge

# Install with uv
uv sync --all-extras --dev

# Run the server
uv run mcp-as-a-judge
```

### **Configuration**

#### **MCP Client Configuration**

**For Claude Desktop / Cursor (SSE Transport):**

```json
{
  "mcpServers": {
    "mcp-as-a-judge": {
      "transport": "sse",
      "url": "http://localhost:8050/sse"
    }
  }
}
```

**For Stdio Transport (Development):**

```json
{
  "mcpServers": {
    "mcp-as-a-judge": {
      "command": "uv",
      "args": ["run", "mcp-as-a-judge"],
      "env": {
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

**For Docker with SSE Transport:**

```json
{
  "mcpServers": {
    "mcp-as-a-judge": {
      "transport": "sse",
      "url": "http://localhost:8050/sse"
    }
  }
}
```

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

**Docker Environment File (.env):**

```bash
# Copy .env.example to .env and customize
cp .env.example .env

# Example .env file:
TRANSPORT=sse
PORT=8050
LOG_LEVEL=INFO
DEBUG=false
```

## 📖 **How It Works**

### **1. Mandatory Workflow Enforcement**

```
User Request → check_swe_compliance → Guided Planning → judge_coding_plan → Implementation → judge_code_change
```

### **2. Obstacle Handling**

```
Agent Hits Blocker → raise_obstacle → User Decision → Continue with User Choice
```

### **3. Requirements Clarification**

```
Unclear Request → elicit_missing_requirements → User Clarification → Proceed with Clear Requirements
```

## 🎯 **Example Usage**

### **Planning Evaluation**

```python
# Agent calls this when user wants to implement something
await judge_coding_plan(
    plan="Detailed implementation steps...",
    design="System architecture and components...",
    research="Analysis of existing solutions...",
    user_requirements="What the user actually wants to achieve",
    context="Additional project context"
)
```

### **Obstacle Resolution**

```python
# Agent calls this when hitting blockers
await raise_obstacle(
    problem="Cannot use LLM sampling - client doesn't support it",
    research="Researched alternatives: configure client, use different client, etc.",
    options=[
        "Configure Cursor to support sampling",
        "Use Claude Desktop instead",
        "Wait for Cursor sampling support",
        "Cancel the evaluation"
    ]
)
```

## 🐳 **Docker Usage Examples**

### **Development with Docker**

```bash
# Start development environment with hot reload
docker-compose --profile development up

# View logs
docker-compose logs -f mcp-as-a-judge-dev

# Stop development environment
docker-compose down
```

### **Production Deployment**

```bash
# Start production environment
docker-compose --profile production up -d

# Check status
docker-compose ps

# View logs
docker-compose logs mcp-as-a-judge

# Update to latest version
docker-compose pull
docker-compose --profile production up -d

# Stop production environment
docker-compose down
```

### **Docker Health Checks**

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' mcp-as-a-judge

# View health check logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' mcp-as-a-judge
```

### **Docker Networking**

```bash
# Run with custom network
docker network create mcp-network
docker run -d \
  --name mcp-as-a-judge \
  --network mcp-network \
  -p 8050:8050 \
  -e TRANSPORT=sse \
  mcp-as-a-judge:latest

# Connect other services to the same network
docker run -d \
  --name nginx-proxy \
  --network mcp-network \
  -p 80:80 \
  nginx:alpine
```

## 🔧 **Development**

### **Project Structure**

```
mcp-as-a-judge/
├── src/mcp_as_a_judge/
│   ├── __init__.py
│   ├── server.py          # Main MCP server implementation
│   └── models.py          # Pydantic models and schemas
├── tests/                 # Test suite
├── docs/                  # Documentation
├── Dockerfile            # Production container
├── docker-compose.yml    # Multi-environment setup
├── pyproject.toml        # Project configuration
└── README.md            # This file
```

### **Running Tests**

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/mcp_as_a_judge

# Run specific test types
uv run pytest -m "not slow"  # Skip slow tests

# Run tests in Docker
docker run --rm \
  -v $(pwd):/app \
  -w /app \
  python:3.12-slim \
  bash -c "pip install uv && uv pip install -e .[dev] && pytest"
```

### **Code Quality**

```bash
# Format code
uv run black src tests

# Lint code
uv run ruff check src tests

# Type checking
uv run mypy src

# All quality checks
make quality
```

## 🌟 **Why This Changes Everything**

### **Before MCP as a Judge:**

- Developers build quick fixes and workarounds
- Insufficient research leads to reinventing existing solutions
- Code doesn't align with actual user requirements
- Bad practices slip through without review

### **After MCP as a Judge:**

- ✅ **Forced deep research** prevents reinventing the wheel
- ✅ **User involvement** ensures requirements alignment
- ✅ **No hidden fallbacks** - transparent decision making
- ✅ **Quality enforcement** at every step
- ✅ **Best practices** become automatic

## 📦 **Installation**

### **From PyPI (Recommended)**

```bash
# Install with uv (recommended)
uv add mcp-as-a-judge

# Or with pip
pip install mcp-as-a-judge
```

### **From Docker**

```bash
# Pull the latest image from GitHub Container Registry
docker pull ghcr.io/hepivax/mcp-as-a-judge:latest

# Run the container
docker run -it --name mcp-as-a-judge ghcr.io/hepivax/mcp-as-a-judge:latest

# Or use docker-compose for production
docker-compose --profile production up -d
```

### **From Source (Development)**

```bash
git clone https://github.com/hepivax/mcp-as-a-judge.git
cd mcp-as-a-judge
uv sync --all-extras --dev
```

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
