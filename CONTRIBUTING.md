# Contributing to Kindle Scribe Notebook Converter

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Virtual environment (venv or conda)

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/downloader.git
cd kindle_notebook_pdf_converter

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install development dependencies
pip install -r requirements-dev.txt
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or for bug fixes:
git checkout -b fix/bug-description
```

### 2. Make Your Changes

- Follow PEP 8 style guidelines
- Add tests for new functionality
- Update documentation as needed
- Keep commits atomic and well-described

### 3. Run Tests and Linting

```bash
# Run tests
pytest tests/ -v --cov

# Format code
black src/ tests/

# Run linter
pylint src/

# Type checking
mypy src/
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add new conversion feature"
# or
git commit -m "fix: resolve issue with stroke decoding"
```

Use conventional commits:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `test:` tests
- `refactor:` code refactoring
- `chore:` maintenance

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then open a pull request on GitHub with:
- Clear description of changes
- Reference to related issues (if any)
- Screenshots for UI changes
- Test results

## Code Style

### Python

- Follow PEP 8
- Use type hints where possible
- Maximum line length: 100 characters
- Use docstrings for all functions and classes

### Example

```python
def decode_stroke_values(data: bytes, num_points: int, name: str = "") -> list[int]:
    """Decode a delta-of-delta-encoded stroke coordinate array.
    
    Args:
        data: Raw bytes of the stroke coordinate field.
        num_points: Expected number of decoded values.
        name: Optional label for error messages.
        
    Returns:
        List of integer coordinate values in canvas units.
        
    Raises:
        ValueError: If the magic signature is invalid.
    """
```

## Testing

- Write tests for all new features
- Maintain or improve code coverage
- Run the full test suite before submitting PR

```bash
pytest tests/ -v --cov --cov-report=html
```

## Documentation

- Update README.md for user-facing changes
- Update docstrings in code
- Add examples to `examples/` directory if applicable

## Reporting Issues

### Bug Reports

Include:
- Clear description of the bug
- Steps to reproduce
- Expected vs. actual behavior
- Python version and OS
- Relevant logs or error messages
- Attached NBK file (if possible, sanitized)

### Feature Requests

Include:
- Clear use case
- Why this feature would be beneficial
- Potential implementation ideas

## Review Process

1. Automated checks run (tests, linting)
2. Maintainers review the code
3. Changes requested if needed
4. Once approved, PR is merged

## Questions?

Feel free to open an issue for questions or discussions.

---

Thank you for contributing!
