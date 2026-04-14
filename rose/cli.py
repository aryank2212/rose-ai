"""
ROSE CLI — command-line input handler with prefix parsing and special commands.
"""

import sys
import threading
import queue

# Windows readline support
try:
    import pyreadline3 as readline
except ImportError:
    try:
        import readline
    except ImportError:
        readline = None

from rose.config import SPECIAL_COMMANDS
from rose import formatter


class CLI:
    """
    Handles CLI input with:
    - rose> prompt
    - Prefix parsing (! for shell, ? for Q&A)
    - Special command detection
    - Shared input queue with voice thread
    """

    def __init__(self, input_queue: queue.Queue):
        self._queue = input_queue
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        """Start the CLI input thread."""
        self._running = True
        self._thread = threading.Thread(target=self._input_loop, daemon=True, name="cli-input")
        self._thread.start()

    def stop(self):
        """Stop the CLI input thread."""
        self._running = False

    def _input_loop(self):
        """Main input loop — reads from stdin and pushes to queue."""
        while self._running:
            try:
                user_input = input("rose> ")
                if not user_input.strip():
                    continue

                self._queue.put({
                    "source": "cli",
                    "text": user_input.strip(),
                })

            except EOFError:
                # Ctrl+Z on Windows
                self._running = False
                self._queue.put({"source": "cli", "text": "sleep", "special": "sleep"})
                break
            except KeyboardInterrupt:
                # Ctrl+C
                print()  # Newline after ^C
                self._queue.put({"source": "cli", "text": "stop", "special": "stop"})


def parse_special_command(text: str) -> str | None:
    """
    Check if text matches a special command.
    Returns the action string or None.
    Handles both "rose, <command>" and bare "<command>" forms.
    """
    cleaned = text.strip().lower()

    # Strip "rose," or "rose " prefix if present
    for prefix in ["rose,", "rose "]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break

    # Look up in special commands
    return SPECIAL_COMMANDS.get(cleaned)


def get_confirmation(prompt: str, timeout: float = 5.0) -> bool:
    """
    Ask for confirmation with a timeout.
    Returns True if user types 'confirm' or 'yes'.
    """
    formatter.ask(prompt)
    result_queue = queue.Queue()

    def _read():
        try:
            resp = input("> ").strip().lower()
            result_queue.put(resp)
        except (EOFError, KeyboardInterrupt):
            result_queue.put("cancel")

    thread = threading.Thread(target=_read, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if result_queue.empty():
        formatter.rose("Confirmation timed out. Action cancelled.")
        return False

    response = result_queue.get()
    return response in ("confirm", "yes", "y")
