"""
ROSE Configuration — all constants, paths, and model definitions.
"""

import os
import shutil
from enum import IntEnum
from pathlib import Path

# ─── Model Configuration ─────────────────────────────────────────────
QUICK_MODEL = os.environ.get("ROSE_QUICK_MODEL", "gemma3:1b")     # Fast Q&A, classification
POWER_MODEL = os.environ.get("ROSE_POWER_MODEL", "gemma4:e4b")    # Tool calling, code gen

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_EXE = os.environ.get("OLLAMA_EXE", shutil.which("ollama") or "ollama")

# ─── Workspace Paths ─────────────────────────────────────────────────
HOME_DIR = Path.home()
WORKSPACE_DIR = HOME_DIR / "rose_workspace"
DOWNLOADS_DIR = WORKSPACE_DIR / "downloads"
BIN_DIR = WORKSPACE_DIR / "bin"
ENV_DIR = WORKSPACE_DIR / "env"
MEMORY_FILE = WORKSPACE_DIR / ".rose_memory.json"
LOG_FILE = WORKSPACE_DIR / ".rose_log.txt"

# ─── Permission Tiers ────────────────────────────────────────────────
class Tier(IntEnum):
    SANDBOX = 0       # Default — workspace only
    ELEVATED = 1      # Home dir read, user-specified write
    FULL_SYSTEM = 2   # Full machine control (30-min window)

TIER_NAMES = {
    Tier.SANDBOX: "Tier 0 (Sandbox)",
    Tier.ELEVATED: "Tier 1 (Elevated)",
    Tier.FULL_SYSTEM: "Tier 2 (Full System)",
}

# ─── Tier 2 Auto-Revoke Timer ────────────────────────────────────────
TIER2_TIMEOUT_SECONDS = 30 * 60  # 30 minutes

# ─── Voice Configuration ─────────────────────────────────────────────
WAKE_WORD = "rose"
SILENCE_THRESHOLD_SECONDS = 1.8
VOICE_ENABLED = False  # Phase 2 — disabled by default

# ─── Agent Configuration ─────────────────────────────────────────────
PLAN_DISPLAY_WAIT_SECONDS = 2  # Seconds to wait after printing plan before executing
MAX_AGENTIC_STEPS = 20         # Safety limit on agentic loop iterations
AUTO_RETRY_ON_FAILURE = True   # Attempt one auto-fix on step failure

# ─── System Prompts ──────────────────────────────────────────────────
CLASSIFIER_SYSTEM_PROMPT = """Classify the user's message as QUICK or COMPLEX. Reply with one word only.

QUICK = questions, facts, explanations, definitions, greetings, opinions, lookups, history, "what is", "who", "why", "explain", "how does X work"
COMPLEX = build, create, write code, make a file, script, deploy, install, download, scrape, fix code, run command, dockerfile, API, automate, debug code

Examples:
"what is a mutex?" -> QUICK
"who invented the internet?" -> QUICK
"explain how TCP works" -> QUICK
"hello" -> QUICK
"build me a REST API" -> COMPLEX
"write a dockerfile" -> COMPLEX
"create a python script" -> COMPLEX
"download this file" -> COMPLEX
"debug this error" -> COMPLEX
"fix my code" -> COMPLEX

Reply QUICK or COMPLEX only."""

QUICK_SYSTEM_PROMPT = """You are ROSE, a helpful AI assistant. Answer in natural language.
Rules:
- Be concise and direct. Short answers are best.
- NEVER respond with code unless the user explicitly asks for code.
- If someone says "hi" or "hello", just greet them back briefly.
- Do not use markdown. Plain text only.
- No filler phrases like "Sure!" or "Great question!" — just answer."""

POWER_SYSTEM_PROMPT = """You are ROSE (Responsive On-device Synthetic Engine), a fully local AI agent.
You are not a chatbot. You are an agent. You plan, execute, build, iterate, and report.
Be direct, efficient, technically precise. No filler. No unnecessary affirmations.

When given a task:
1. Reason through it silently
2. Produce a concrete plan
3. Use your available tools to execute step by step
4. Return a clear result

You have tools for: shell commands, file read/write, web requests, downloads, and system info.
Always check permissions before operating on paths outside the workspace.
Do NOT use markdown formatting — output plain text for a terminal.
For code blocks, use plain fenced blocks with the language label."""

# ─── Special Commands ─────────────────────────────────────────────────
SPECIAL_COMMANDS = {
    # Tier escalation
    "i trust you completely": "tier_1_escalate",
    "take control of my machine": "tier_2_escalate",
    "stand down": "tier_revoke",

    # Session control
    "sleep": "sleep",
    "stop": "stop",
    "forget that": "forget_last",
    "what are you doing": "status",
    "what are you doing?": "status",

    # Memory
    "what do you remember about me": "memory_show",
    "what do you remember about me?": "memory_show",
    "forget everything about me": "memory_clear",

    # Model override
    "think harder": "force_power",
    "go deep": "force_power",
    "use gemma4": "force_power",
    "quick answer": "force_quick",
    "quick answer only": "force_quick",
}
