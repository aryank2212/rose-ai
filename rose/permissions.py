"""
ROSE Permission System — tiered access control (Tier 0/1/2).
"""

import threading
from pathlib import Path

from rose.config import Tier, TIER_NAMES, TIER2_TIMEOUT_SECONDS, WORKSPACE_DIR, HOME_DIR
from rose import formatter


class PermissionManager:
    """Manages the current permission tier and validates operations."""

    def __init__(self):
        self._tier: Tier = Tier.SANDBOX
        self._tier2_timer: threading.Timer | None = None
        self._elevated_write_dirs: list[Path] = []  # User-granted write dirs for Tier 1
        self._lock = threading.Lock()

    @property
    def tier(self) -> Tier:
        return self._tier

    @property
    def tier_name(self) -> str:
        return TIER_NAMES[self._tier]

    def escalate_to_tier1(self):
        """Escalate to Tier 1 (Elevated). Session-scoped."""
        with self._lock:
            self._tier = Tier.ELEVATED
        formatter.rose("Elevated access granted for this session. Say \"rose, sleep\" to revoke.")

    def escalate_to_tier2(self, confirmed: bool = False):
        """
        Escalate to Tier 2 (Full System).
        Requires explicit confirmation. Auto-revokes after 30 minutes.
        """
        if not confirmed:
            formatter.warn(
                "Full system access requested. This gives me control of your entire "
                "filesystem, processes, and display.\n"
                "       Type \"confirm\" within 5 seconds to proceed, or type \"cancel\"."
            )
            return False

        with self._lock:
            self._tier = Tier.FULL_SYSTEM
            # Start auto-revoke timer
            if self._tier2_timer and self._tier2_timer.is_alive():
                self._tier2_timer.cancel()
            self._tier2_timer = threading.Timer(TIER2_TIMEOUT_SECONDS, self._auto_revoke_tier2)
            self._tier2_timer.daemon = True
            self._tier2_timer.start()

        formatter.rose(
            "Full system access active. Auto-revokes in 30 minutes. "
            "Type \"rose, stand down\" to revoke early."
        )
        return True

    def revoke(self):
        """Revoke back to Tier 0 (Sandbox)."""
        with self._lock:
            self._tier = Tier.SANDBOX
            if self._tier2_timer and self._tier2_timer.is_alive():
                self._tier2_timer.cancel()
                self._tier2_timer = None
            self._elevated_write_dirs.clear()
        formatter.tier_change(self.tier_name, "All elevated permissions revoked.")

    def _auto_revoke_tier2(self):
        """Called by timer — auto-revoke Tier 2 after timeout."""
        with self._lock:
            if self._tier == Tier.FULL_SYSTEM:
                self._tier = Tier.SANDBOX
                self._tier2_timer = None
        formatter.warn("Tier 2 access has auto-expired after 30 minutes. Back to Sandbox.")

    def grant_write_dir(self, path: Path):
        """Grant Tier 1 write access to a specific directory."""
        resolved = Path(path).resolve()
        if resolved not in self._elevated_write_dirs:
            self._elevated_write_dirs.append(resolved)
            formatter.rose(f"Write access granted to: {resolved}")

    # ─── Path Validation ─────────────────────────────────────────────

    def can_read(self, path: str | Path) -> bool:
        """Check if current tier allows reading the given path."""
        resolved = Path(path).resolve()
        workspace = WORKSPACE_DIR.resolve()

        if self._tier >= Tier.FULL_SYSTEM:
            return True
        if self._is_within(resolved, workspace):
            return True  # Always readable in workspace
        if self._tier >= Tier.ELEVATED and self._is_within(resolved, HOME_DIR):
            return True  # Tier 1+ can read home dir
        return False

    def can_write(self, path: str | Path) -> bool:
        """Check if current tier allows writing to the given path."""
        resolved = Path(path).resolve()
        workspace = WORKSPACE_DIR.resolve()

        if self._tier >= Tier.FULL_SYSTEM:
            return True
        if self._is_within(resolved, workspace):
            return True  # Always writable in workspace
        if self._tier >= Tier.ELEVATED:
            # Check user-granted write directories
            for allowed in self._elevated_write_dirs:
                if self._is_within(resolved, allowed):
                    return True
            # Standard locations at Tier 1
            for std_dir in ["Downloads", "Desktop", "Documents"]:
                std_path = HOME_DIR / std_dir
                if std_path.exists() and self._is_within(resolved, std_path):
                    return True
        return False

    def can_execute_shell(self, command: str) -> bool:
        """Check if shell command is allowed at current tier."""
        # At any tier, basic commands are fine if they don't target system paths
        dangerous_patterns = ["rm -rf /", "del /s /q C:\\", "format ", "fdisk",
                              "rmdir /s", "shutdown", "reg delete"]
        cmd_lower = command.lower().strip()

        for pattern in dangerous_patterns:
            if pattern in cmd_lower:
                if self._tier < Tier.FULL_SYSTEM:
                    return False
                # Even at Tier 2, flag for confirmation
                formatter.warn(f"Destructive command detected: {command}")
                return True  # Allow but warn — caller should confirm

        return True

    def can_kill_process(self) -> bool:
        """Only Tier 2 can kill external processes."""
        return self._tier >= Tier.FULL_SYSTEM

    def can_launch_app(self) -> bool:
        """Tier 1+ can launch GUI apps."""
        return self._tier >= Tier.ELEVATED

    def can_access_clipboard(self) -> bool:
        """Tier 1+ can access clipboard."""
        return self._tier >= Tier.ELEVATED

    def require_tier(self, required: Tier, action: str) -> bool:
        """Check if current tier meets requirement. Print error if not."""
        if self._tier >= required:
            return True
        formatter.err(
            f"Action '{action}' requires {TIER_NAMES[required]}, "
            f"but current access is {self.tier_name}."
        )
        return False

    @staticmethod
    def _is_within(path: Path, parent: Path) -> bool:
        """Check if path is within parent directory."""
        try:
            path.resolve().relative_to(parent.resolve())
            return True
        except ValueError:
            return False
