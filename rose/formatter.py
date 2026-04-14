"""
ROSE Output Formatter — terminal-native, prefixed, color-enhanced output.
"""

import sys

# Fix Windows console encoding for Unicode characters (smart quotes, etc.)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Try colorama for Windows terminal color support
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False

# ─── Color Definitions ───────────────────────────────────────────────
if HAS_COLOR:
    C_ROSE = Fore.CYAN + Style.BRIGHT
    C_YOU = Fore.GREEN + Style.BRIGHT
    C_PLAN = Fore.YELLOW + Style.BRIGHT
    C_STEP = Fore.YELLOW
    C_DONE = Fore.GREEN + Style.BRIGHT
    C_ERR = Fore.RED + Style.BRIGHT
    C_ASK = Fore.MAGENTA + Style.BRIGHT
    C_SOURCE = Fore.BLUE
    C_WARN = Fore.RED + Style.BRIGHT
    C_DIM = Style.DIM
    C_RESET = Style.RESET_ALL
else:
    C_ROSE = C_YOU = C_PLAN = C_STEP = C_DONE = ""
    C_ERR = C_ASK = C_SOURCE = C_WARN = C_DIM = C_RESET = ""


def rose(msg: str):
    """Print a ROSE status/response message."""
    print(f"{C_ROSE}[ROSE]{C_RESET} {msg}")


def you(msg: str):
    """Print transcribed user voice input."""
    print(f"{C_YOU}[YOU]{C_RESET}  {msg}")


def plan(steps: list[str]):
    """Print a numbered plan before execution."""
    print(f"{C_PLAN}[PLAN]{C_RESET}")
    for i, step in enumerate(steps, 1):
        print(f"  {C_PLAN}{i}.{C_RESET} {step}")
    print()


def step(current: int, total: int, msg: str):
    """Print step progress during agentic execution."""
    print(f"{C_STEP}[STEP]{C_RESET} {current}/{total}: {msg}")


def done(msg: str):
    """Print task completion summary."""
    print(f"{C_DONE}[DONE]{C_RESET} {msg}")


def err(msg: str):
    """Print error message."""
    print(f"{C_ERR}[ERR]{C_RESET}  {msg}")


def ask(msg: str):
    """Print question to user (only when truly needed)."""
    print(f"{C_ASK}[ASK]{C_RESET}  {msg}")


def source(url: str):
    """Print source URL citation."""
    print(f"{C_SOURCE}[SOURCE]{C_RESET} {url}")


def warn(msg: str):
    """Print warning message."""
    print(f"{C_WARN}[WARN]{C_RESET} {msg}")


def stream_token(token: str):
    """Print a single streamed token (no newline, flush immediately)."""
    sys.stdout.write(token)
    sys.stdout.flush()


def stream_start():
    """Start a streamed response — print the ROSE prefix."""
    sys.stdout.write(f"{C_ROSE}[ROSE]{C_RESET} ")
    sys.stdout.flush()


def stream_end():
    """End a streamed response — ensure newline."""
    print()


def banner(tier_name: str):
    """Print the ROSE startup banner."""
    print(f"""{C_ROSE}
╔══════════════════════════════════════════╗
║  ROSE — Responsive On-device Synth. Eng. ║
║  Model : gemma3:1b / gemma4:e4b (Ollama) ║
║  Access: {tier_name:<32s}║
║  Wake  : "rose" — mic is {"live" if True else "off":<14s}║
║  Workspace: ~/rose_workspace/            ║
╚══════════════════════════════════════════╝{C_RESET}
""")


def listening():
    """Print voice listening indicator."""
    print(f"{C_ROSE}[ROSE]{C_RESET} 🎙  Listening...")


def tier_change(tier_name: str, msg: str = ""):
    """Print tier change notification."""
    extra = f" {msg}" if msg else ""
    rose(f"Access level changed to {tier_name}.{extra}")
