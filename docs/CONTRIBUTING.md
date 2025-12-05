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

3. **Install dependencies**

   **Option A: Using pip-tools (recommended)**

   ```bash
   # Install pip-tools for dependency management
   pip install pip-tools

   # Install all dependencies including dev tools
   pip install -r requirements.lock
   python -m pip install -e .[dev]
   ```

   **Option B: Using Poetry**

   ```bash
   poetry install --with dev
   ```

4. **Verify installation**

   ```bash
   python -m jira_importer --version
   python -m jira_importer --help
   ```

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

### Running the Application

1. **Basic usage**

   ```bash
   python -m jira_importer path/to/your/file.xlsx
   ```

2. **Debug mode** (detailed logging)

   ```bash
   python -m jira_importer path/to/your/file.xlsx --debug
   ```

3. **Auto-fix enabled** (automatic issue resolution)

   ```bash
   python -m jira_importer path/to/your/file.xlsx --auto-fix
   ```

4. **Cloud import** (direct to Jira Cloud)

   ```bash
   python -m jira_importer path/to/your/file.xlsx --cloud
   ```

5. **Credential management**

   ```bash
   python -m jira_importer --credentials run    # Set up credentials
   python -m jira_importer --credentials show   # View stored credentials
   python -m jira_importer --credentials clear  # Clear credentials
   ```

### Testing Your Changes

1. **Use sample data**
   - Copy `resources/templates/ImportTemplate.xlsx` to your working directory
   - Modify it with test data
   - Run the importer on your test file

2. **Enable debug mode**
   - Use the `--debug` flag for detailed logging
   - Check console output for information

3. **Test cloud integration**
   - Set up credentials with `--credentials run`
   - Test with `--cloud` flag
   - Verify authentication and API calls

### Building

1. **Development build** (for testing)

   ```bash
   python build.py -c dev
   ```

2. **Production build** (for distribution)

   ```bash
   python build.py -c shipping
   ```

3. **Using Poetry** (alternative build method)

   ```bash
   poetry build --format pyinstaller
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

## 🧪 Testing Guidelines

### Manual Testing

1. Test with various Excel file formats
2. Verify CSV output format
3. Test configuration file variations
4. Test error handling scenarios
5. Test auto-fix functionality with `--auto-fix` flag
6. Test cloud integration features

### Sample Data

- Use the template under `resources/templates/ImportTemplate.xlsx` for test data
- Create test cases with different data scenarios
- Test edge cases and error conditions
- Test with real-world data when possible

### Automated Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=jira_importer

# Run specific test file
pytest tests/test_specific_module.py
```

## 🐛 Debugging and Troubleshooting

### Debug Mode

Enable detailed logging and debugging information:

- Use `--debug` or `-d` command line flag
- Provides detailed logging and extra output
- Shows internal processing steps and validation details

### Common Development Issues

1. **Import errors**: Ensure all dependencies are installed with `pip install -r requirements.lock`
2. **File not found**: Check file paths and permissions
3. **Configuration issues**: Verify JSON syntax in config files
4. **Authentication errors**: Use `--credentials show` to check stored credentials
5. **Cloud import failures**: Verify Jira permissions and project access
6. **Path validation errors**: Ensure file paths don't contain control characters
7. **Sensitive data in logs**: Sensitive information is automatically redacted for security

### Testing Configuration

Before running imports, test your setup:

```bash
# Test configuration without processing data
python -m jira_importer --show-config

# Test data processing without writing output files
python -m jira_importer path/to/test.xlsx --dry-run

# Test with debug information
python -m jira_importer path/to/test.xlsx --debug
```

## 📦 Dependency Management

### Current Dependencies

The project uses dependencies for comprehensive functionality:

**Direct Dependencies:**

- **Data processing**: pandas, openpyxl
- **UI/Console**: rich, rich-argparse, tqdm, colorlog, colorama
- **HTTP/API**: requests
- **Security**: keyring
- **Logging**: structlog, colorlog
- **Configuration**: PyYAML

**Development Dependencies:**

- **Testing**: pytest, pytest-cov
- **Code quality**: black, isort, mypy, ruff, pylint
- **Build tools**: pip-tools, poetry, pyinstaller

### Managing Dependencies

**Using pip-tools (recommended):**

```bash
# Update to latest versions
pip-compile --upgrade requirements.in

# Refresh with current constraints
pip-compile requirements.in

# Install dependencies
pip install -r requirements.lock
```

**Using Poetry:**

```bash
# Install dependencies
poetry install --with dev

# Update dependencies
poetry update
```

### Adding New Dependencies

1. Add to `requirements.in` (for pip-tools) or `pyproject.toml` (for Poetry)
2. Run `pip-compile requirements.in` or `poetry lock`
3. Commit both files

## 🚀 Release Process

### Building for Distribution

1. **Development Build**: `python build.py -c dev`
2. **Production Build**: `python build.py -c shipping`
3. **Poetry Build**: `poetry build --format pyinstaller`

### Version Management

- Update version information via `build/version/generate_version.py`
- Follow semantic versioning principles
- Update documentation for new features
- Test thoroughly before release

## 🤝 Pull Request Process

### Before Submitting

1. **Fork the repository** and create a feature branch
2. **Make your changes** following the code style guidelines
3. **Test your changes** thoroughly
4. **Update documentation** if needed
5. **Commit your changes** with clear commit messages

### Pull Request Guidelines

- **Clear title**: Use descriptive titles like "Add: feature description" or "Fix: bug description"
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

## 🔮 Future Development

### Planned Features

- **Mac and Linux support** - Native builds for other operating systems
- **Multiple file imports** - Process several Excel files at once
- **Project templates** - Ready-made templates for common project types
- **OAuth 2.0 authentication** - Enhanced authentication options
- **Advanced reporting** - More detailed import reports and analytics

### Architecture Considerations

- The pipeline is designed for easy extension
- Maintain backward compatibility where possible
- Consider performance for large datasets
- Plan for API integration features

---

**Thank you for contributing to the Jira Importer Toolkit!** 🎉

*This contributing guide is maintained by the Jira Importer Toolkit development team.*

:_GeneratedFile_
