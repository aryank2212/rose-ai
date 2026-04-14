"""
ROSE Memory — persistent session memory stored in JSON.
"""

import json
import time
from pathlib import Path

from rose.config import MEMORY_FILE
from rose import formatter


class Memory:
    """Manages persistent user preferences and context across sessions."""

    def __init__(self):
        self._data: dict = {
            "preferences": {},       # e.g., {"language": "python", "style": "type_hints"}
            "projects": {},          # e.g., {"kaal": "D:\\Github\\Hackathons\\KAAL"}
            "constraints": [],       # e.g., ["always use type hints", "never use jQuery"]
            "frequent_urls": [],     # e.g., ["https://api.example.com"]
            "session_count": 0,
            "last_session": None,
        }
        self._dirty = False

    def load(self):
        """Load memory from disk. Create file if it doesn't exist."""
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # Merge with defaults (in case schema evolved)
                for key in self._data:
                    if key in saved:
                        self._data[key] = saved[key]
                formatter.rose(f"Memory loaded ({len(self._data['preferences'])} preferences, "
                               f"{len(self._data['projects'])} projects).")
            except (json.JSONDecodeError, IOError) as e:
                formatter.err(f"Failed to load memory: {e}. Starting fresh.")
        else:
            formatter.rose("No previous memory found. Starting fresh.")

        # Update session tracking
        self._data["session_count"] += 1
        self._data["last_session"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.save()

    def save(self):
        """Save memory to disk."""
        try:
            MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            self._dirty = False
        except IOError as e:
            formatter.err(f"Failed to save memory: {e}")

    def set_preference(self, key: str, value: str):
        """Set a user preference."""
        self._data["preferences"][key] = value
        self._dirty = True
        self.save()

    def get_preference(self, key: str, default=None) -> str | None:
        """Get a user preference."""
        return self._data["preferences"].get(key, default)

    def add_constraint(self, constraint: str):
        """Add a user-stated constraint/rule."""
        if constraint not in self._data["constraints"]:
            self._data["constraints"].append(constraint)
            self._dirty = True
            self.save()

    def register_project(self, name: str, path: str):
        """Register a named project location."""
        self._data["projects"][name] = path
        self._dirty = True
        self.save()

    def add_url(self, url: str):
        """Add a frequently used URL."""
        if url not in self._data["frequent_urls"]:
            self._data["frequent_urls"].append(url)
            self._dirty = True
            self.save()

    def show(self) -> str:
        """Return a human-readable summary of stored memory."""
        lines = []
        prefs = self._data["preferences"]
        if prefs:
            lines.append("Preferences:")
            for k, v in prefs.items():
                lines.append(f"  - {k}: {v}")

        projects = self._data["projects"]
        if projects:
            lines.append("Projects:")
            for name, path in projects.items():
                lines.append(f"  - {name}: {path}")

        constraints = self._data["constraints"]
        if constraints:
            lines.append("Your rules:")
            for c in constraints:
                lines.append(f"  - {c}")

        urls = self._data["frequent_urls"]
        if urls:
            lines.append("Frequent URLs:")
            for u in urls:
                lines.append(f"  - {u}")

        lines.append(f"Sessions: {self._data['session_count']}")
        lines.append(f"Last session: {self._data['last_session']}")

        return "\n".join(lines) if lines else "I don't have any stored memory about you yet."

    def clear(self):
        """Clear all memory."""
        self._data = {
            "preferences": {},
            "projects": {},
            "constraints": [],
            "frequent_urls": [],
            "session_count": 0,
            "last_session": None,
        }
        self.save()
        formatter.rose("All memory cleared.")

    def get_context_for_prompt(self) -> str:
        """Return memory context to inject into model system prompts."""
        parts = []
        prefs = self._data["preferences"]
        if prefs:
            parts.append("User preferences: " + ", ".join(f"{k}={v}" for k, v in prefs.items()))
        constraints = self._data["constraints"]
        if constraints:
            parts.append("User rules: " + "; ".join(constraints))
        return "\n".join(parts) if parts else ""
