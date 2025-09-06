# Contributing to MCP as a Judge

Thank you for your interest in contributing to MCP as a Judge! This document provides guidelines for contributing to this project.

## 🎯 **Project Vision**

MCP as a Judge aims to revolutionize software development by preventing bad coding practices through AI-powered evaluation and user-driven decision making. Every contribution should align with this vision of improving code quality and developer workflows.

## 🚀 **Getting Started**

### **Prerequisites**

- Python 3.13.5+ (latest secure version)
- uv (recommended) or pip
- Git
- A compatible MCP client for testing

### **Development Setup**

1. **Fork and clone the repository:**

```bash
git clone https://github.com/OtherVibes/mcp-as-a-judge.git
cd mcp-as-a-judge
```

2. **Set up development environment:**

```bash
# Install uv if you don't have it
pip install uv

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

3. **Install pre-commit hooks:**

```bash
pre-commit install
```

4. **Verify setup:**

```bash
# Run tests
uv run pytest

# Check code quality
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
```

## 📝 **Development Guidelines**

### **Code Style**

- Follow PEP 8 and use Ruff for formatting
- Use type hints for all function parameters and return values
- Write comprehensive docstrings for all public functions and classes
- Keep line length to 88 characters (Ruff default)

### **Testing**

- Write tests for all new functionality
- Maintain test coverage above 80%
- Use descriptive test names that explain what is being tested
- Include both unit tests and integration tests

### **Documentation**

- Update README.md for user-facing changes
- Add docstrings to all new functions and classes
- Update type hints and model schemas
- Include examples in docstrings where helpful

## 🔧 **Types of Contributions**

### **🐛 Bug Fixes**

- Check existing issues before creating new ones
- Include steps to reproduce the bug
- Add tests that verify the fix
- Update documentation if needed

### **✨ New Features**

- Discuss major features in an issue first
- Ensure features align with project vision
- Include comprehensive tests
- Update documentation and examples

### **📚 Documentation**

- Fix typos and improve clarity
- Add examples and use cases
- Improve setup instructions
- Translate documentation (if applicable)

### **🧪 Testing**

- Add missing test coverage
- Improve test quality and reliability
- Add integration tests
- Performance testing

## 🔄 **Development Workflow**

### **1. Create a Branch**

Use semantic branch naming that follows our conventions:

```bash
# For new features
git checkout -b feat/your-feature-name

# For bug fixes
git checkout -b fix/bug-description

# For documentation updates
git checkout -b docs/documentation-improvement

# For refactoring
git checkout -b refactor/code-improvement

# For tests
git checkout -b test/test-improvement

# For chores/maintenance
git checkout -b chore/maintenance-task
```

**Valid Branch Name Patterns:**
- `feat/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation changes
- `test/*` - Test additions/improvements
- `refactor/*` - Code refactoring
- `chore/*` - Maintenance tasks
- `style/*` - Code formatting changes

### **2. Make Changes**

- Write code following the style guidelines
- Add tests for your changes
- Update documentation as needed
- Run tests locally to ensure everything works

### **3. Quality Checks**

Run the complete CI pipeline locally:

```bash
# Format code
uv run ruff format src tests

# Check linting
uv run ruff check src tests

# Type checking
uv run mypy src

# Run tests
uv run pytest

# Check coverage
uv run pytest --cov=src/mcp_as_a_judge

# Secret scanning (requires gitleaks)
gitleaks detect --redact -v --exit-code=2 --log-level=warn
```

### **3.1. Running GitHub Actions Locally with Act**

You can test the complete CI pipeline locally using [act](https://github.com/nektos/act):

```bash
# Install act (macOS)
brew install act

# Install act (Linux)
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Install act (Windows)
choco install act-cli
```

**Run GitHub Actions locally:**

```bash
# List available workflows and jobs
act -l

# Run specific workflow (dry run to test syntax)
act -W .github/workflows/validate-conventions.yml --dryrun

# Run specific job (dry run)
act -j validate-branch-name --dryrun

# Run with verbose output
act -v

# Test simple workflows
act -W .github/workflows/validate-conventions.yml
```

**Act Configuration:**

The project includes `.actrc` file with optimized settings:

```bash
# .actrc (already configured)
--container-architecture linux/amd64
--artifact-server-path /tmp/artifacts
-P ubuntu-latest=catthehacker/ubuntu:act-latest
```

**Current Limitations:**
- ⚠️ Full CI workflow requires modern Node.js features not available in act's containers
- ✅ Simple validation workflows work perfectly
- ✅ Use local CI pipeline for complete testing (see "One-Command CI Execution" above)

**Benefits of using Act:**
- ✅ Test workflow syntax before pushing
- ✅ Debug simple workflow issues locally
- ✅ Validate branch naming and commit conventions
- ✅ Quick iteration on workflow improvements

**Recommended Approach:**
1. Use **local CI pipeline** for complete testing
2. Use **act** for workflow syntax validation
3. Push to GitHub for full CI validation

### **4. Commit Changes**

```bash
git add .
git commit -m "feat: add user requirements alignment to judge tools"
```

**Commit Message Format:**

Follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test additions/changes
- `refactor:` for code refactoring
- `style:` for formatting changes
- `chore:` for maintenance tasks
- `ci:` for CI/CD changes
- `perf:` for performance improvements

**Examples:**
```bash
feat: add LLM fallback support for judge tools
fix: resolve type checking errors in messaging layer
docs: update contribution guidelines with act instructions
test: add integration tests for workflow guidance
ci: improve GitHub Actions performance with caching
```

### **5. Push and Create PR**

```bash
git push origin your-branch-name
```

Then create a Pull Request on GitHub with:

- Clear description of changes
- Link to related issues
- Screenshots/examples if applicable
- Checklist of completed items

## 🚀 **Complete CI Pipeline**

### **One-Command CI Execution**

Run the complete CI pipeline locally with one command:

```bash
# Complete CI validation (all checks)
cd /path/to/mcp-as-a-judge && \
echo "🚀 COMPLETE CI PIPELINE" && \
echo "======================" && \
uv run ruff check src tests && echo "✅ Linting: PASSED" && \
uv run ruff format --check src tests && echo "✅ Formatting: PASSED" && \
uv run mypy src && echo "✅ Type Checking: PASSED" && \
uv run pytest --tb=no -q && echo "✅ Tests: PASSED" && \
gitleaks detect --redact -v --exit-code=2 --log-level=warn >/dev/null 2>&1 && echo "✅ Secret Scanning: PASSED" && \
echo "🎉 ALL CI CHECKS COMPLETED!"
```

### **CI Pipeline Components**

Our CI pipeline includes:

1. **Code Quality** (Linting & Formatting)
   - Ruff linting for code quality
   - Ruff formatting for consistent style
   - MyPy type checking for type safety

2. **Test Suite**
   - 125+ comprehensive tests
   - Unit and integration tests
   - 100% test success rate required

3. **Security Scanning**
   - Gitleaks for secret detection
   - Bandit for security vulnerabilities
   - SARIF reporting for GitHub Security

4. **Build Validation**
   - Docker multi-architecture builds
   - Package building and validation
   - Dependency resolution checks

## 🧪 **Testing Guidelines**

### **Running Tests**

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_server.py

# Run with coverage
uv run pytest --cov=src/mcp_as_a_judge

# Run only fast tests
uv run pytest -m "not slow"
```

### **Writing Tests**

- Use descriptive test names: `test_judge_coding_plan_with_user_requirements`
- Test both success and failure cases
- Mock external dependencies
- Use fixtures for common test data
- Test edge cases and error conditions

## 📋 **Pull Request Checklist**

Before submitting a PR, ensure:

- [ ] Code follows style guidelines (Ruff format, Ruff check, MyPy pass)
- [ ] All tests pass locally (125/125 tests passing)
- [ ] GitHub Actions CI passes (test with `act` locally)
- [ ] New functionality has comprehensive tests
- [ ] Documentation is updated
- [ ] Commit messages follow Conventional Commits format
- [ ] Branch name follows semantic naming convention
- [ ] PR description is clear and complete
- [ ] No breaking changes (or clearly documented with migration guide)
- [ ] Performance impact considered and tested
- [ ] Secret scanning passes (no sensitive data committed)

## 🚨 **Important Guidelines**

### **User Requirements Focus**

- All judge tools must consider user requirements alignment
- New features should enhance user-driven decision making
- Avoid hidden fallbacks - always involve users in critical decisions

### **Quality Standards**

- Maintain high code quality standards
- Ensure comprehensive error handling
- Follow software engineering best practices
- Write maintainable, readable code

### **Backward Compatibility**

- Avoid breaking changes when possible
- Deprecate features before removing them
- Provide migration guides for breaking changes
- Maintain API stability

## 🤝 **Community Guidelines**

- Be respectful and inclusive
- Help newcomers get started
- Share knowledge and best practices
- Provide constructive feedback
- Follow the Code of Conduct

## 📞 **Getting Help**

- **Issues**: Create GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Documentation**: Check the README and inline documentation
- **Examples**: Look at existing tests and code for patterns

## 🎉 **Recognition**

Contributors will be recognized in:

- README.md contributors section
- Release notes for significant contributions
- GitHub contributor graphs
- Special mentions for major features

Thank you for helping make MCP as a Judge better for everyone! 🚀
