# Contributing to ROSE

Thank you for your interest in contributing to ROSE! This project is open source and we welcome contributions of all kinds.

## Getting Started

1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/ROSE.git
   cd ROSE
   ```
3. **Install** in development mode:
   ```bash
   pip install -e ".[dev]"
   ```
4. **Install Ollama** and pull the required models:
   ```bash
   ollama pull gemma3:1b
   ollama pull gemma4:e4b
   ```

## Development

### Project Structure

```
rose/
├── config.py        # Constants, model names, system prompts
├── main.py          # Entry point, startup, event loop
├── cli.py           # CLI input handling
├── voice.py         # Voice pipeline (Phase 2)
├── router.py        # Dual-model routing logic
├── models.py        # Ollama API wrapper
├── tools.py         # Tool definitions for gemma4
├── executor.py      # Agentic loop engine
├── permissions.py   # Tiered permission system
├── memory.py        # Persistent memory
├── formatter.py     # CLI output formatting
└── web.py           # Web utilities
```

### Running Tests

```bash
python -m pytest tests/
```

### Code Style

- We use [Ruff](https://github.com/astral-sh/ruff) for linting
- Type hints are encouraged
- Keep functions focused and documented
- Follow existing code patterns

```bash
ruff check rose/
ruff format rose/
```

## What to Contribute

### Good First Issues
- Add more tool definitions in `tools.py`
- Improve classification accuracy in `router.py`
- Add more special voice/CLI commands
- Write tests

### Larger Contributions
- **Voice Pipeline (Phase 2)**: Complete the wake word + STT implementation in `voice.py`
- **TTS Output**: Add text-to-speech response mode
- **Plugin System**: Allow users to add custom tools
- **Multi-platform**: Test and fix issues on macOS/Linux

## Guidelines

1. **Keep it local-first** — ROSE runs entirely on the user's machine. Don't add cloud dependencies.
2. **Respect the permission system** — All file/system operations must check the current permission tier.
3. **No telemetry** — Never add tracking, analytics, or data collection.
4. **Security** — Never store credentials in plain text. Never exfiltrate user data.

## Pull Requests

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes with clear commit messages
3. Ensure tests pass
4. Submit a PR with a description of what changed and why

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
