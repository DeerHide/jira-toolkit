# Developer Starter Guide

Welcome to the Jira Importer Toolkit development team! This guide will help you get started with contributing to the project.

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Git** for version control
- **pip** for package management
- **Windows** (primary development platform)

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone git@github.com:DeerHide/jira-toolkit.git
   cd jira-toolkit
   ```

2. **Create and activate virtual environment**
   ```bash
   # Create virtual environment
   python -m venv .venv
   
   # Activate virtual environment
   # On Windows:
   .venv\Scripts\activate
   
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**
   ```bash
   python -m jira_importer --version
   ```

## 📁 Project Structure

```
jira-toolkit/
├── src/jira_importer/          # Main application code
│   ├── main.py                 # Entry point
│   ├── app.py                  # Application logic
│   ├── config.py               # Configuration management
│   ├── csvprocessor.py         # CSV processing logic
│   ├── fileops.py              # File operations
│   ├── artifacts.py            # Artifact management
│   ├── userio.py               # User interaction
│   ├── log.py                  # Logging utilities
│   └── utils.py                # Utility functions
├── build/                      # Build assets and working dirs
│   ├── configs/                # Build configurations (dev.json, shipping.json)
│   ├── icons/                  # Application icons
│   ├── version/                # Version management (generate_version.py, VSVersionInfo)
│   └── temp/                   # Ephemeral staging area for builds (gitignored)
├── dist/                       # Build output (per-config subfolders: dev/, shipping/)
├── rsc/                        # Runtime/user resources
│   └── templates/              # Template files (config_importer.json, ImportTemplate.xlsx, jira-config.json)
├── docs/                       # Documentation
├── scripts/                    # Helper scripts (placeholder for future dev tooling)
├── build.py                    # Build script entrypoint
├── requirements.txt            # Python dependencies
├── README.md                   # User documentation
└── .venv/                      # Virtual environment (created during setup)
```

## 🛠️ Development Workflow

### Running the Application

1. **Basic usage**
   ```bash
   python main.py path/to/your/file.xlsx
   ```

2. **With debug mode**
   ```bash
   python main.py path/to/your/file.xlsx -d
   ```

3. **With custom configuration**
   ```bash
   python main.py path/to/your/file.xlsx -c config.json
   ```

### Testing Your Changes

1. **Use the sample template**
   - Copy `rsc/templates/ImportTemplate.xlsx` to your working directory
   - Modify it with test data
   - Run the importer on your test file

2. **Enable debug mode**
   - Use the `-d` or `--debug` flag for detailed logging
   - Check console output for detailed information

### Building the Executable

1. **Development build**
   ```bash
   python build.py -c dev
   ```

2. **Production build**
   ```bash
   python build.py -c shipping
   ```

## 🔧 Key Components

### Configuration System (`config.py`)
- Manages application configuration from JSON files
- Supports multiple configuration sources
- Handles validation and defaults

### CSV Processor (`csvprocessor.py`)
- Core logic for Excel to CSV conversion
- Data validation and formatting
- Jira-specific formatting rules

### File Operations (`fileops.py`)
- Excel to CSV conversion
- File path management
- Output file generation

### Logging (`log.py`)
- Structured logging with colorama support
- Debug mode support
- Configurable log levels

## 🐛 Debugging

### Debug Mode
The application supports debug mode which can be triggered by:
- Using `-d` or `--debug` command line flag
- This enables detailed logging and additional output

### Common Issues

1. **Import errors**: Ensure all dependencies are installed
2. **File not found**: Check file paths and permissions
3. **Configuration issues**: Verify JSON syntax in config files

### Logging
- Debug logs provide detailed execution information
- Use `logging.debug()` for development debugging
- Check console output for error messages

## 📝 Code Style Guidelines

### Python Conventions
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and concise

### File Organization
- Each module should have a single responsibility
- Use clear imports and avoid circular dependencies
- Maintain consistent error handling patterns

### Comments and Documentation
- Add comments for complex logic
- Update docstrings when changing function signatures
- Keep README.md updated with user-facing changes

## 🧪 Testing

### Manual Testing
1. Test with various Excel file formats
2. Verify CSV output format
3. Test configuration file variations
4. Test error handling scenarios

### Sample Data
- Use the template under `resources/templates/ImportTemplate.xlsx` to craft test data
- Create test cases with different data scenarios
- Test edge cases and error conditions

## 🔄 Contribution Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
- Follow the code style guidelines
- Test your changes thoroughly
- Update documentation if needed

3. **Test your build**
   ```bash
   python build.py -c dev
   ```

4. **Submit a pull request**
- Include a clear description of changes
- Reference any related issues
- Ensure all tests pass

## 📦 Dependencies

### Core Dependencies
- `pandas`: Data manipulation and Excel processing
- `openpyxl`: Excel file reading
- `tqdm`: Progress bars
- `colorama`: Cross-platform colored terminal output
- `structlog`: Structured logging
- `rich`: Rich console output

### Development Dependencies
- `pyinstaller`: For building executables
- `logging`: Built-in Python logging

## 🚀 Deployment

### Building for Distribution
1. Use the shipping configuration for production builds
2. Test the executable thoroughly before distribution
3. Verify all dependencies are included

### Version Management
- Update version information via `build/version/generate_version.py`
- Follow semantic versioning principles
- Update documentation for new features

## 📞 Getting Help

- Check the debug logs for detailed error information
- Review the main README.md for user documentation
- Create issues for bugs or feature requests
- Reach out to the development team for questions

## 🔮 Future Development

### Planned Features
- Cross-platform support (Mac/Linux)
- Direct Jira Cloud API integration
- Batch processing capabilities
- Import templates for common project types

### Architecture Considerations
- Keep the modular design for easy extension
- Maintain backward compatibility
- Consider performance for large datasets
- Plan for API integration features

---

**Happy coding!** 🎉
