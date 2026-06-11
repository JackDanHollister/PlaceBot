# Contributing to PlaceBot

Thank you for your interest in contributing to PlaceBot! This document provides guidelines and instructions for contributing.

## 🤝 Ways to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, PlaceBot version)
- Sample locality data (if applicable)

### Suggesting Features

Feature requests are welcome! Please include:
- Clear description of the feature
- Use case and motivation
- Example usage (if applicable)
- Impact on existing functionality

### Contributing Code

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed
4. **Test your changes**
   ```bash
   pytest tests/
   ```
5. **Commit with clear messages**
   ```bash
   git commit -m "Add: Brief description of changes"
   ```
6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request**

## 📋 Development Setup

```bash
# Clone your fork
git clone https://github.com/JackDanHollister/PlaceBot.git
cd PlaceBot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with GUI and local-model extras
pip install -e ".[dev,gui,local]"

# Run tests
pytest tests/
```

## 🎨 Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and single-purpose
- Comment complex logic

### Code Formatting

We use `black` for code formatting:

```bash
black placebot/
```

### Linting

We use `flake8` for linting:

```bash
flake8 placebot/
```

## 🧪 Testing

- Write tests for all new functionality
- Ensure existing tests pass
- Aim for high code coverage
- Test with multiple AI models when applicable

Run tests:
```bash
# All tests
pytest tests/

# With coverage
pytest --cov=placebot tests/

# Specific test file
pytest tests/test_specific.py
```

## 📖 Documentation

- Update README.md for user-facing changes
- Add docstrings to new functions/classes
- Update CHANGELOG.md with your changes
- Include examples in docstrings

## 🔧 Adding New AI Models

To add support for a new AI model:

1. Create a new file in `placebot/models/`:
   ```python
   # placebot/models/new_model.py
   def process_locality(locality_desc, api_key):
       """Process locality with New Model."""
       # Implementation here
       pass
   ```

2. Add model configuration in `placebot/core/ai_processor.py`

3. Update model comparison in `placebot/core/model_comparison.py`

4. Add tests in `tests/`

5. Update documentation

## 🌐 Adding New Features

When adding new features:

1. Ensure backward compatibility
2. Follow existing patterns in the codebase
3. Add configuration options when appropriate
4. Update CLI help text
5. Add examples to documentation

## 📝 Commit Message Guidelines

Use clear, descriptive commit messages:

- `Add: New feature description`
- `Fix: Bug fix description`
- `Update: Changes to existing feature`
- `Docs: Documentation changes`
- `Test: Test additions or modifications`
- `Refactor: Code refactoring`

## 🤔 Questions?

If you have questions:
- Open an issue with the "question" label
- Start a discussion on GitHub Discussions
- Check existing issues and documentation

## 📜 Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Help others learn and grow

## 🎯 Priority Areas

Current priority areas for contribution:

1. **Performance Optimization**
   - Batch processing improvements
   - Caching strategies
   - Rate limit handling

2. **Model Integration**
   - Additional AI vendors
   - Model-specific optimizations
   - Cost tracking improvements

3. **Testing**
   - Increased test coverage
   - Integration tests
   - Performance benchmarks

4. **Documentation**
   - Usage examples
   - Tutorial content
   - API documentation

5. **Error Handling**
   - Better error messages
   - Recovery strategies
   - Validation improvements

## 🏆 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Credited in release notes
- Acknowledged in documentation

Thank you for contributing to PlaceBot! 🌍
