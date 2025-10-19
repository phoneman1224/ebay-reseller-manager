# Contributing to eBay Reseller Manager

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- A clear title and description
- Steps to reproduce the problem
- Expected vs actual behavior
- Screenshots if applicable
- Your environment (OS, Python version, etc.)

### Suggesting Features

Feature requests are welcome! Please:
- Check if the feature has already been requested
- Provide a clear description of the feature
- Explain why it would be useful
- Include mockups or examples if possible

### Pull Requests

1. Fork the repository
2. Create a new branch (`git checkout -b feature/YourFeature`)
3. Make your changes
4. Add tests if applicable
5. Ensure all tests pass
6. Commit your changes (`git commit -m 'Add some feature'`)
7. Push to your branch (`git push origin feature/YourFeature`)
8. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Comment complex logic
- Keep functions focused and concise

### Testing

- Add unit tests for new features
- Ensure existing tests pass
- Run tests with: `python -m pytest tests/`

### Commit Messages

Use clear, descriptive commit messages:
- `feat: Add pricing calculator feature`
- `fix: Correct database path resolution`
- `docs: Update README with installation steps`
- `test: Add tests for inventory management`

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/ebay-reseller-manager.git
cd ebay-reseller-manager

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black flake8

# Run tests
python -m pytest tests/

# Run the application
python3 src/main.py
```

## Project Structure

```
ebay-reseller-manager/
├── data/              # Database storage
├── src/               # Source code
│   ├── gui/          # GUI modules
│   ├── models/       # Data models
│   ├── database.py   # Database handler
│   └── main.py       # Entry point
├── tests/            # Unit tests
└── docs/             # Documentation
```

## Questions?

Feel free to open an issue for any questions or discussions!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
