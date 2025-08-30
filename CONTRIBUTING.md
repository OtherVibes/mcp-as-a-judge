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
git clone https://github.com/hepivax/mcp-as-a-judge.git
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
uv run black --check src tests
uv run ruff check src tests
uv run mypy src
```

## 📝 **Development Guidelines**

### **Code Style**

- Follow PEP 8 and use Black for formatting
- Use type hints for all function parameters and return values
- Write comprehensive docstrings for all public functions and classes
- Keep line length to 88 characters (Black default)

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

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### **2. Make Changes**

- Write code following the style guidelines
- Add tests for your changes
- Update documentation as needed
- Run tests locally to ensure everything works

### **3. Quality Checks**

```bash
# Format code
uv run black src tests

# Check linting
uv run ruff check src tests

# Type checking
uv run mypy src

# Run tests
uv run pytest

# Check coverage
uv run pytest --cov=src/mcp_as_a_judge
```

### **4. Commit Changes**

```bash
git add .
git commit -m "feat: add user requirements alignment to judge tools"
```

**Commit Message Format:**

- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test additions/changes
- `refactor:` for code refactoring
- `style:` for formatting changes
- `chore:` for maintenance tasks

### **5. Push and Create PR**

```bash
git push origin your-branch-name
```

Then create a Pull Request on GitHub with:

- Clear description of changes
- Link to related issues
- Screenshots/examples if applicable
- Checklist of completed items

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

- [ ] Code follows style guidelines (Black, Ruff, MyPy pass)
- [ ] All tests pass locally
- [ ] New functionality has tests
- [ ] Documentation is updated
- [ ] Commit messages follow the format
- [ ] PR description is clear and complete
- [ ] No breaking changes (or clearly documented)
- [ ] Performance impact considered

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
