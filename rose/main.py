"""
ROSE Main — entry point. Startup sequence, main event loop.
Runs CLI on main thread to avoid prompt/response interleaving.
"""

import os
import sys
import time
import queue
import signal
import subprocess

from rose.config import (
    WORKSPACE_DIR, DOWNLOADS_DIR, BIN_DIR, ENV_DIR,
    OLLAMA_HOST, OLLAMA_EXE, VOICE_ENABLED,
)
from rose import formatter
from rose.permissions import PermissionManager
from rose.memory import Memory
from rose.models import ModelClient
from rose.router import Router
from rose.tools import ToolRegistry
from rose.executor import Executor
from rose.cli import parse_special_command, get_confirmation
from rose.voice import VoiceListener


class Rose:
    """Main ROSE application."""

    def __init__(self):
        self._input_queue: queue.Queue = queue.Queue()  # For voice input only
        self._permissions = PermissionManager()
        self._memory = Memory()
        self._model: ModelClient | None = None
        self._router: Router | None = None
        self._tools: ToolRegistry | None = None
        self._executor: Executor | None = None
        self._voice: VoiceListener | None = None
        self._running = False
        self._tier2_pending = False

    def startup(self):
        """Run the full startup sequence."""
        # 1. Print banner
        formatter.banner(self._permissions.tier_name)

        # 2. Ensure workspace directories exist
        self._ensure_workspace()

        # 3. Check Ollama is running
        if not self._check_ollama():
            return False

        # 4. Load memory
        self._memory.load()

        # 5. Initialize components
        self._model = ModelClient(memory_context=self._memory.get_context_for_prompt())
        self._router = Router(self._model)
        self._tools = ToolRegistry(self._permissions)
        self._executor = Executor(self._model, self._tools)

        # 6. Verify models are available
        if not self._model.verify_models():
            formatter.err("Required models not found. Run: ollama pull gemma3:1b && ollama pull gemma4:e4b")
            return False

        # 7. Start voice listener (background thread, if enabled)
        self._voice = VoiceListener(self._input_queue)
        self._voice.start()

        formatter.rose("Ready. Listening.")
        print()
        return True

    def run(self):
        """Main event loop — CLI runs on main thread."""
        if not self.startup():
            return

        self._running = True

        # Handle Ctrl+C gracefully
        signal.signal(signal.SIGINT, self._signal_handler)

        try:
            while self._running:
                # Check for voice input first (non-blocking)
                try:
                    voice_event = self._input_queue.get_nowait()
                    text = voice_event.get("text", "").strip()
                    if text:
                        self._handle_input(text, "voice")
                        continue
                except queue.Empty:
                    pass

                # CLI input on main thread — blocks until user types
                try:
                    user_input = input("rose> ")
                except EOFError:
                    break
                except KeyboardInterrupt:
                    print()
                    if self._executor and self._executor.is_running:
                        self._executor.stop()
                    else:
                        formatter.rose("Shutting down...")
                        self._running = False
                    continue

                text = user_input.strip()
                if not text:
                    continue

                self._handle_input(text, "cli")

        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def _handle_input(self, text: str, source: str):
        """Process a single input (from CLI or voice)."""

        # ─── Check for special commands ───────────────────────────
        special = parse_special_command(text)

        if special:
            self._handle_special(special, text)
            return

        # ─── Handle pending Tier 2 confirmation ──────────────────
        if self._tier2_pending:
            self._tier2_pending = False
            if text.lower() in ("confirm", "yes", "y"):
                self._permissions.escalate_to_tier2(confirmed=True)
            else:
                formatter.rose("Tier 2 escalation cancelled.")
            return

        # ─── Route input to appropriate model ─────────────────────
        route = self._router.route(text)

        if route == "shell":
            # Raw shell passthrough
            cmd = self._router.strip_prefix(text)
            self._execute_shell(cmd)

        elif route == "qa":
            # Pure Q&A — gemma3:1b, no action
            clean_text = self._router.strip_prefix(text)
            self._model.quick_chat(clean_text)

        elif route == "quick":
            # Quick response — gemma3:1b
            self._model.quick_chat(text)

        elif route == "power":
            # Complex task — gemma4:e4b with tools
            self._executor.execute(text)

        print()  # Blank line after response for readability

    def _handle_special(self, action: str, original_text: str):
        """Handle a special command action."""
        if action == "tier_1_escalate":
            self._permissions.escalate_to_tier1()

        elif action == "tier_2_escalate":
            self._permissions.escalate_to_tier2(confirmed=False)
            self._tier2_pending = True

        elif action == "tier_revoke":
            self._permissions.revoke()

        elif action == "sleep":
            formatter.rose("Going to sleep. Session ended.")
            self._permissions.revoke()
            self._running = False

        elif action == "stop":
            if self._executor and self._executor.is_running:
                self._executor.stop()
            else:
                formatter.rose("Nothing running to stop.")

        elif action == "forget_last":
            self._model.discard_last_exchange()
            formatter.rose("Last exchange discarded.")

        elif action == "status":
            if self._executor:
                formatter.rose(self._executor.get_status())
            else:
                formatter.rose("Idle.")

        elif action == "memory_show":
            formatter.rose(self._memory.show())

        elif action == "memory_clear":
            self._memory.clear()

        elif action == "force_power":
            self._router.set_force_mode("power")

        elif action == "force_quick":
            self._router.set_force_mode("quick")

    def _execute_shell(self, command: str):
        """Execute a raw shell command."""
        if not self._permissions.can_execute_shell(command):
            formatter.err(f"Command blocked at {self._permissions.tier_name}.")
            return

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(WORKSPACE_DIR),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                formatter.err(result.stderr.strip())
            if result.returncode != 0:
                formatter.err(f"Exit code: {result.returncode}")
        except subprocess.TimeoutExpired:
            formatter.err("Command timed out after 60 seconds.")
        except Exception as e:
            formatter.err(str(e))

    def _ensure_workspace(self):
        """Create workspace directories if they don't exist."""
        for d in [WORKSPACE_DIR, DOWNLOADS_DIR, BIN_DIR, ENV_DIR]:
            d.mkdir(parents=True, exist_ok=True)
        formatter.rose(f"Workspace: {WORKSPACE_DIR}")

    def _check_ollama(self) -> bool:
        """Verify Ollama is running. Attempt to start it if not."""
        try:
            import httpx
            resp = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
            if resp.status_code == 200:
                return True
        except Exception:
            pass

        # Try to start Ollama
        formatter.rose("Ollama not detected. Attempting to start...")
        try:
            if os.path.exists(OLLAMA_EXE):
                subprocess.Popen(
                    [OLLAMA_EXE, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
                # Wait for it to come up
                for _ in range(15):
                    time.sleep(1)
                    try:
                        import httpx
                        resp = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
                        if resp.status_code == 200:
                            formatter.rose("Ollama started successfully.")
                            return True
                    except Exception:
                        continue

            formatter.err(
                f"Could not start Ollama. Please run '{OLLAMA_EXE} serve' manually."
            )
            return False

        except Exception as e:
            formatter.err(f"Failed to start Ollama: {e}")
            return False

    def _signal_handler(self, sig, frame):
        """Handle Ctrl+C."""
        if self._executor and self._executor.is_running:
            self._executor.stop()
        else:
            print()
            formatter.rose("Shutting down...")
            self._running = False

    def shutdown(self):
        """Clean shutdown."""
        self._running = False
        if self._voice:
            self._voice.stop()
        if self._memory:
            self._memory.save()
        formatter.rose("Goodbye.")


def main():
    """Entry point."""
    rose = Rose()
    rose.run()


if __name__ == "__main__":
    main()
