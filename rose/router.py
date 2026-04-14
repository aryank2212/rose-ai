"""
ROSE Router — decides which model to use based on input analysis.
"""

from rose import formatter


class Router:
    """
    Routes user input to the appropriate model:
    - gemma3:1b for quick Q&A (default)
    - gemma4:e4b for complex/tool tasks
    - Gemma3 can self-escalate to gemma4 via classification
    """

    # Keywords that force the power model (checked first)
    FORCE_POWER_KEYWORDS = [
        "build ", "create a ", "scaffold", "write a script", "write a ",
        "make a ", "develop ", "implement ", "code a ", "set up ",
        "deploy", "containerize", "dockerfile", "docker",
        "debug this", "fix this code", "fix this ", "refactor",
        "search the web", "download ", "fetch from",
        "run this", "execute ", "install ",
        "scrape ", "automate ", "generate a ",
    ]

    # Patterns that force the quick model (skip classification entirely)
    FORCE_QUICK_PATTERNS = [
        "what is ", "what are ", "what's ", "who is ", "who are ",
        "why is ", "why do ", "why does ", "when did ", "when was ",
        "how does ", "how do ", "how is ", "where is ", "where do ",
        "explain ", "define ", "describe ", "tell me about ",
        "meaning of ", "difference between ",
    ]

    def __init__(self, model_client):
        self._client = model_client
        self._force_mode: str | None = None  # "quick" or "power" override

    def set_force_mode(self, mode: str | None):
        """
        Set a one-shot override for the next routing decision.
        mode: "quick", "power", or None (auto)
        """
        self._force_mode = mode
        if mode == "power":
            formatter.rose("Next response will use gemma4:e4b (power model).")
        elif mode == "quick":
            formatter.rose("Next response will use gemma3:1b (quick model).")

    def route(self, user_input: str) -> str:
        """
        Determine which model should handle this input.

        Returns:
            "quick"  — use gemma3:1b
            "power"  — use gemma4:e4b
            "shell"  — raw shell passthrough (no model)
            "qa"     — pure Q&A with gemma3:1b (no action)
        """
        stripped = user_input.strip()

        # ─── Prefix-based routing ─────────────────────────────────
        if stripped.startswith("!"):
            return "shell"

        if stripped.startswith("?"):
            return "qa"

        # ─── User override (one-shot) ────────────────────────────
        if self._force_mode:
            mode = self._force_mode
            self._force_mode = None  # Reset after use
            return mode

        # ─── Quick pattern heuristic (skip classification) ─────────
        lower = stripped.lower()
        for pattern in self.FORCE_QUICK_PATTERNS:
            if lower.startswith(pattern):
                return "quick"

        # ─── Power keyword heuristic (fast pre-check) ─────────────
        for keyword in self.FORCE_POWER_KEYWORDS:
            if keyword in lower:
                formatter.rose(f"Routing to gemma4:e4b (detected: \"{keyword}\")")
                return "power"

        # ─── Short inputs default to quick (< 5 words) ────────────
        if len(lower.split()) <= 4:
            return "quick"

        # ─── Gemma3 classification (the self-escalation) ──────────
        classification = self._client.classify(stripped)

        if classification == "COMPLEX":
            formatter.rose("gemma3 escalated this to gemma4:e4b (classified as complex task)")
            return "power"

        return "quick"

    def strip_prefix(self, user_input: str) -> str:
        """Remove the ! or ? prefix from input if present."""
        stripped = user_input.strip()
        if stripped.startswith("!") or stripped.startswith("?"):
            return stripped[1:].strip()
        return stripped
