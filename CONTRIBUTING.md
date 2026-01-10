# Contributing to Maestro V2

Thank you for your interest in contributing to Maestro V2! 🎉

## How to Contribute

### Reporting Bugs

1. Check existing [Issues](https://github.com/simplehima/maestro-agents/issues) first
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)

### Suggesting Features

1. Open an issue with the `enhancement` label
2. Describe the feature and its use case
3. Explain why it would benefit users

### Pull Requests

1. Fork the repository
2. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes
4. Run tests:
   ```bash
   python -m pytest tests/ -v
   ```
5. Commit with clear messages:
   ```bash
   git commit -m "Add: description of change"
   ```
6. Push and open a Pull Request

### Code Style

- Follow PEP 8 for Python
- Use type hints where possible
- Add docstrings to functions and classes
- Keep functions focused and small

### Adding New Agents

1. Create your agent class in `agents/specialized.py`
2. Extend `BaseAgent` and implement `execute()`
3. Register in `create_all_agents()`
4. Add to frontend agent grid

### Adding New Tools

1. Create tool in `tools/` directory
2. Extend `BaseTool` and implement `execute()`
3. Add registration function
4. Document in README

## Development Setup

```bash
# Clone and setup
git clone https://github.com/simplehima/maestro-agents.git
cd maestro-agents
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Run development server
python app.py
```

## Questions?

Open an issue or reach out to [@simplehima](https://github.com/simplehima).

Thank you for contributing! 🙏
