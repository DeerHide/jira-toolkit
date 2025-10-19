# Contributing Guide

This doc tells you how to contribute to the project.

## 🚀 Quick Start

### What You Need

- **Python 3.12+** (updated from 3.10+)
- **Git** for version control
- **pip** for package management
- **Cross-platform** (Windows, macOS, Linux)

### Setup Steps

1. **Grab the code**

   ```bash
   git clone git@github.com:DeerHide/jira-toolkit.git
   cd jira-toolkit
   ```

2. **Set up your environment**

   ```bash
   # Create virtual environment
   python3 -m venv .venv

   # Activate it
   # On Windows:
   .venv\Scripts\activate

   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install stuff**

   ```bash
   pip install -r requirements.lock
   ```

   **Note**: The project now uses Poetry for dependency management. You can also use:

   ```bash
   poetry install --with dev
   ```

4. **Check it works**

   ```bash
   python3 -m jira_importer -h
   ```

## 🛠️ Development Workflow

### Running the App

1. **Basic usage**

   ```bash
   python3 -m jira_importer path/to/your/file.xlsx
   ```

2. **With debug mode**

   ```bash
   python3 -m jira_importer path/to/your/file.xlsx -d
   ```

3. **With custom configuration**

   ```bash
   python3 -m jira_importer path/to/your/file.xlsx -c config.json
   ```

4. **With auto-fix enabled**

   ```bash
   python3 -m jira_importer path/to/your/file.xlsx --auto-fix
   ```

5. **With cloud import**

   ```bash
   python3 -m jira_importer path/to/your/file.xlsx --cloud
   ```

6. **With credential management**

   ```bash
   python3 -m jira_importer --credentials run
   python3 -m jira_importer --credentials show
   python3 -m jira_importer --credentials clear
   ```

### Testing Your Changes

1. **Use the sample template**
   - Copy `resources/templates/ImportTemplate.xlsx` to your working directory
   - Modify it with test data
   - Run the importer on your test file

2. **Enable debug mode**
   - Use the `-d` or `--debug` flag for logging
   - Check console output for information

### Building

1. **Development build**

   ```bash
   python3 build.py -c dev
   ```

2. **Production build**

   ```bash
   python3 build.py -c shipping
   ```

## 📝 Code Style Guidelines

### Python Conventions

- Try to sitck with the PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes when deemed relevant
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
5. Test auto-fix functionality with `--auto-fix` flag

### Sample Data

- Use the template under `resources/templates/ImportTemplate.xlsx` to craft test data
- Create test cases with different data scenarios
- Test edge cases and error conditions

## 🐛 Debugging

### Debug Mode

Turn on debug mode with:

- `-d` or `--debug` command line flag
- Gives you detailed logging and extra output

### Common Issues

1. **Import errors**: Make sure all dependencies are installed
2. **File not found**: Check file paths and permissions
3. **Configuration issues**: Verify JSON syntax in config files
4. **Line ending issues**: If builds fail or you get cross-platform problems, check that all text files use LF line endings

### Logging

- Debug logs give you detailed execution info
- Use `logging.debug()` for development debugging
- Check console output for error messages

## 📦 Dependencies

### Core Dependencies

See requirements files

### Development Dependencies

See requirements files

## 🚀 Deployment

### Building for Distribution

1. Use the shipping configuration for production builds
2. Test the executable thoroughly before distribution

### Version Management

- Update version information via `build/version/generate_version.py`
- Follow semantic versioning principles
- Update documentation for new features

## 📞 Need Help?

- Check the debug logs for detailed error info
- Look at the main README.md for user docs
- Create issues for bugs or feature requests
- Reach out to the dev team with questions

## 🔮 Future Development

### Planned Features

- Excel-defined validation rules ✅ **Implemented**
- Direct Jira Cloud API integration ✅ **Implemented**
- Batch processing capabilities ✅ **Implemented**
- Import templates for common project types
- OAuth 2.0 authentication (scaffolded)
- Advanced credential management ✅ **Implemented**

### New Development Features

#### Cloud Integration Development

- **Credential Management**: Use `--credentials` command for testing authentication
- **OAuth 2.0**: Scaffolded for future implementation
- **Batch Processing**: Test with large datasets using `--cloud` flag
- **Excel Table Configuration**: Use `-ce` flag to test Excel-based configuration

#### New Command Line Options

- **`--credentials`**: Test credential management features
- **`--auto-fix`**: Test automatic fixing capabilities
- **`--fix-cloud-estimates`**: Test Jira Cloud ×60 estimate handling
- **`--enable-excel-rules`**: Test Excel-based validation rules
- **`--data-sheet`**: Test custom data sheet names

### Architecture Considerations

- The new pipeline is designed for easy extension
- Maintain backward compatibility where possible
- Consider performance for large datasets
- Plan for API integration features

---

**Happy coding!** 🎉
