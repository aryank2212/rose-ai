<div align="center">

#   ROSE

**Responsive On-device Synthetic Engine**

A fully local, privacy-first AI assistant powered by Ollama with dual-model intelligence.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Ollama](https://img.shields.io/badge/Ollama-local%20AI-green.svg)](https://ollama.com)

</div>

---

## What is ROSE?

ROSE is not a chatbot. It's an **agent**. It plans, executes, builds, iterates, and reports — running entirely on your machine with zero cloud dependencies.

It uses **two local models** intelligently:
- ⚡ **Quick model** (gemma3:1b, 815MB) — instant answers for questions, lookups, conversations
- 🔧 **Power model** (gemma4:e4b, 9.6GB) — tool calling, code generation, multi-step tasks

ROSE automatically routes every request to the right model. Simple questions get instant answers. Complex tasks activate the full agent with tool calling. You can also swap in any Ollama-compatible models via environment variables.

## Features

- **Dual-Model Routing** — 4-layer intelligence routing (pattern match → keyword detection → short-input filter → LLM classification)
- **Tool Calling** — Shell commands, file I/O, web requests, downloads, system info — all through native Ollama tool calling
- **Agentic Execution** — plan → execute → evaluate → adjust → report loops for complex tasks
- **Tiered Permissions** — Sandbox (default) → Elevated → Full System, with auto-revoke timers
- **Persistent Memory** — Remembers your preferences, projects, and rules across sessions
- **Privacy-First** — Everything runs locally. No data leaves your machine.
- **Voice Ready** — Wake word + speech-to-text pipeline designed (Phase 2)

## Quick Start

### Prerequisites

- [Python 3.10+](https://www.python.org/downloads/)
- [Ollama](https://ollama.com) installed and running

### Install

```bash
# Clone the repo
git clone https://github.com/aryank2212/ROSE.git
cd ROSE

# Install ROSE
pip install -e .

# Pull the models
ollama pull gemma3:1b
ollama pull gemma4:e4b
```

### Run

```bash
# Make sure Ollama is serving
ollama serve

# Launch ROSE
rose
# or: python -m rose.main
```

You'll see:

```
╔══════════════════════════════════════════╗
║  ROSE — Responsive On-device Synth. Eng. ║
║  Model : gemma3:1b / gemma4:e4b (Ollama) ║
║  Access: Tier 0 (Sandbox)                ║
║  Workspace: ~/rose_workspace/            ║
╚══════════════════════════════════════════╝

[ROSE] Ready. Listening.
rose>
```

## Usage

### Input Modes

| Prefix | Mode | Model | Example |
|--------|------|-------|---------|
| *(none)* | Agentic | Auto-routed | `rose> build me a flask API` |
| `?` | Q&A only | gemma3:1b | `rose> ?what is a POSIX semaphore` |
| `!` | Shell passthrough | None | `rose> !ls -la` |

### Model Routing

ROSE decides which model to use automatically:

```
"what is a mutex?"              → gemma3:1b  (instant, ~1s)
"explain how TCP works"         → gemma3:1b  (instant, ~1s)
"build me a REST API in Python" → gemma4:e4b (tools + agentic loop)
"debug this python error"       → gemma4:e4b (tools + agentic loop)
```

Override anytime:
- `think harder` / `go deep` / `use gemma4` → forces gemma4 for next response
- `quick answer` → forces gemma3 for next response

### Permission Tiers

| Tier | Name | How to Activate | Access |
|------|------|-----------------|--------|
| 0 | Sandbox | Default | `~/rose_workspace/` only |
| 1 | Elevated | `"I trust you completely"` | Home directory read, standard folders write |
| 2 | Full System | `"take control of my machine"` + confirm | Everything (auto-revokes in 30 min) |

### Special Commands

| Command | Action |
|---------|--------|
| `rose, sleep` | End session |
| `rose, stop` | Abort current task |
| `rose, stand down` | Revoke permissions |
| `rose, what are you doing?` | Current task status |
| `rose, forget that` | Discard last exchange |
| `what do you remember about me?` | Show stored memory |
| `forget everything about me` | Clear all memory |

## Architecture

```
User Input (CLI / Voice)
        │
   ┌────▼────────────────────┐
   │ Router                  │
   │  ├─ "!" → shell         │
   │  ├─ "?" → Q&A (gemma3)  │
   │  ├─ Quick patterns      │──→ gemma3:1b (instant)
   │  ├─ Power keywords      │──→ gemma4:e4b (tools)
   │  ├─ Short input (≤4w)   │──→ gemma3:1b (instant)
   │  └─ LLM classification  │──→ gemma3 decides → escalate?
   └─────────────────────────┘
              │
    ┌─────────▼──────────┐
    │   gemma4:e4b       │
    │   + Tool Registry  │──→ shell, files, web, downloads...
    │   + Executor       │──→ plan → execute → evaluate → report
    └────────────────────┘
```

## Configuration

All settings can be overridden via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ROSE_QUICK_MODEL` | `gemma3:1b` | Model for quick responses |
| `ROSE_POWER_MODEL` | `gemma4:e4b` | Model for complex tasks |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_EXE` | Auto-detected | Path to Ollama executable |

### Use Different Models

```bash
# Use Qwen instead of Gemma
export ROSE_QUICK_MODEL="qwen3:4b"
export ROSE_POWER_MODEL="qwen3:8b"
rose
```

## Voice Mode (Phase 2)

Voice support is designed but disabled by default. To enable:

```bash
# Install voice dependencies
pip install -e ".[voice]"

# Set VOICE_ENABLED in config or environment
```

Requires: PyAudio, faster-whisper, openwakeword

## Project Structure

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

## Security

- **Local only** — No data ever leaves your machine
- **No telemetry** — Zero tracking, analytics, or data collection
- **No credential storage** — Passwords and API keys are never saved to disk
- **Permission tiers** — Graduated access control with auto-revocation
- **Destructive action protection** — Double confirmation required for irreversible operations

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE) — use it, fork it, build on it.

---

<div align="center">
<i>Built with 🌹 by the community. Runs on your machine, stays on your machine.</i>
</div>
