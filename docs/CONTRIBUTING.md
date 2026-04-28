# Contributing to Jira Importer Toolkit

Thank you for your interest in contributing to the Jira Importer Toolkit! This guide will help you get started with contributing to the project.

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+** (required for modern features and performance)
- **Git** for version control
- **pip** or **Poetry** for package management
- **Cross-platform** development (Windows, macOS, Linux)
- **Jira Cloud account** (for testing cloud integration features)

### Setup Steps

1. **Fork and clone the repository**

   ```bash
   # Fork the repository on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/jira-toolkit.git
   cd jira-toolkit

   # Add upstream remote
   git remote add upstream https://github.com/DeerHide/jira-toolkit.git
   ```

2. **Set up your development environment**

   ```bash
   # Create virtual environment
   python -m venv .venv

   # Activate it
   # On Windows:
   .venv\Scripts\activate

   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies (Poetry-first)**

   ```bash
   poetry install
   poetry install --extras dev
   ```

   Alternative (supported): pip-tools + editable install

   ```bash
   pip install pip-tools
   pip install -r requirements.lock
   python -m pip install -e .[dev]
   ```

4. **Verify installation**

   ```bash
   python -m jira_importer --version
   python -m jira_importer --help
   ```

   Note: `python -m jira_importer` requires the package to be installed in the active environment
   (for example via `python -m pip install -e .` or `poetry install`).

For day-to-day development commands, runtime options, builds, debugging, and dependency details, use `docs/DEV.md` as the primary reference.

## 🛠️ Development Workflow

### Making Changes

1. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**
   - Write code following the project's style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**

   ```bash
   # Run tests
   pytest

   # Test the application
   python -m jira_importer --version
   python -m jira_importer path/to/test.xlsx --dry-run
   ```

4. **Commit your changes**

   ```bash
   git add .
   git commit -m "Add: brief description of your changes"
   ```

5. **Push and create a pull request**

   ```bash
   git push origin feature/your-feature-name
   # Then create a PR on GitHub
   ```

### Run Tests Before Opening a PR

```bash
pytest
python -m jira_importer --version
python -m jira_importer path/to/test.xlsx --dry-run
```

## 📝 Code Style Guidelines

### Python Conventions

- Follow **PEP 8** style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes when relevant
- Keep functions focused and concise
- Use type hints where appropriate

### File Organization

- Each module should have a single responsibility
- Use clear imports and avoid circular dependencies
- Maintain consistent error handling patterns
- Follow the existing project structure

### Comments and Documentation

- Add comments for complex logic
- Update docstrings when changing function signatures
- Keep README.md updated with user-facing changes
- Update this contributing guide when adding new processes

## Scope of This Guide

This document covers contribution workflow, review expectations, and pull request hygiene.  
For execution details (all runtime flags, debug flows, builds, release mechanics, and full dependency management), see `docs/DEV.md`.

## 🤝 Pull Request Process

### Before Submitting

1. **Fork the repository** and create a feature branch
2. **Make your changes** following the code style guidelines
3. **Test your changes** thoroughly
4. **Update documentation** if needed
5. **Commit your changes** with clear commit messages

### Pull Request Guidelines

- **Clear title**: Use descriptive titles that state behavior change and intent
- **Detailed description**: Explain what changes you made and why
- **Testing**: Describe how you tested your changes
- **Documentation**: Update relevant documentation files
- **Breaking changes**: Clearly mark any breaking changes

### Review Process

- All pull requests require review from maintainers
- Address feedback promptly
- Keep pull requests focused and reasonably sized
- Ensure all CI checks pass

## 📞 Getting Help

### Development Support

- Check debug logs for detailed error information
- Review the main README.md for user documentation
- Create issues for bugs or feature requests
- Reach out to the development team with questions

### Community

- **GitHub Repository**: <https://github.com/DeerHide/jira-toolkit>
- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Discussions**: Use GitHub Discussions for questions and community support

**Thank you for contributing to the Jira Importer Toolkit!** 🎉

*This contributing guide is maintained by the Jira Importer Toolkit development team.*

:_GeneratedFile_
