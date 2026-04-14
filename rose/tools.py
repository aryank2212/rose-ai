"""
ROSE Tools — tool definitions for gemma4:e4b tool calling.
Each tool checks permissions before executing.
"""

import os
import json
import platform
import subprocess
import shutil
import psutil
from pathlib import Path

from rose.config import WORKSPACE_DIR, DOWNLOADS_DIR
from rose import formatter


class ToolRegistry:
    """Registers and executes tools, checking permissions via PermissionManager."""

    def __init__(self, permissions):
        self._permissions = permissions
        self._tools_map: dict = {}
        self._register_all()

    def _register_all(self):
        """Register all available tool functions."""
        self._tools_map = {
            "run_shell": self.run_shell,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "list_directory": self.list_directory,
            "create_directory": self.create_directory,
            "web_request": self.web_request,
            "download_file": self.download_file,
            "system_info": self.system_info,
            "search_files": self.search_files,
        }

    def get_tool_functions(self) -> list:
        """Return the list of Python functions for Ollama tool calling."""
        return [
            self.run_shell,
            self.read_file,
            self.write_file,
            self.list_directory,
            self.create_directory,
            self.web_request,
            self.download_file,
            self.system_info,
            self.search_files,
        ]

    def execute(self, tool_name: str, args: dict) -> str:
        """Execute a tool by name with the given arguments."""
        func = self._tools_map.get(tool_name)
        if not func:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        try:
            result = func(**args)
            return result if isinstance(result, str) else json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ─── Tool Implementations ────────────────────────────────────────

    def run_shell(self, command: str, working_directory: str = "") -> str:
        """Run a shell command. By default runs in the workspace directory. Returns stdout and stderr."""
        cwd = working_directory or str(WORKSPACE_DIR)
        target_path = Path(cwd).resolve()

        # Permission check: workspace is always allowed, outside requires permission
        if not self._permissions.can_read(target_path):
            return json.dumps({"error": f"Permission denied: cannot execute in {cwd} at current tier."})

        if not self._permissions.can_execute_shell(command):
            return json.dumps({"error": f"Permission denied: command blocked at current tier."})

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = {
                "stdout": result.stdout[:4000] if result.stdout else "",
                "stderr": result.stderr[:2000] if result.stderr else "",
                "returncode": result.returncode,
            }
            return json.dumps(output)
        except subprocess.TimeoutExpired:
            return json.dumps({"error": "Command timed out after 60 seconds."})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def read_file(self, path: str) -> str:
        """Read the contents of a file. Returns the file content as a string."""
        target = Path(path).resolve()

        if not self._permissions.can_read(target):
            return json.dumps({"error": f"Permission denied: cannot read {path} at current tier."})

        try:
            if not target.exists():
                return json.dumps({"error": f"File not found: {path}"})
            if target.stat().st_size > 500_000:  # 500KB limit
                return json.dumps({"error": f"File too large ({target.stat().st_size} bytes). Max 500KB."})
            content = target.read_text(encoding="utf-8", errors="replace")
            return content
        except Exception as e:
            return json.dumps({"error": str(e)})

    def write_file(self, path: str, content: str) -> str:
        """Write content to a file. Creates parent directories if needed. Returns success status."""
        target = Path(path).resolve()

        if not self._permissions.can_write(target):
            return json.dumps({"error": f"Permission denied: cannot write to {path} at current tier."})

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return json.dumps({"success": True, "path": str(target), "bytes": len(content.encode("utf-8"))})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def list_directory(self, path: str = "") -> str:
        """List the contents of a directory. Returns file names, types, and sizes."""
        target = Path(path or str(WORKSPACE_DIR)).resolve()

        if not self._permissions.can_read(target):
            return json.dumps({"error": f"Permission denied: cannot read {path} at current tier."})

        try:
            if not target.exists():
                return json.dumps({"error": f"Directory not found: {path}"})
            if not target.is_dir():
                return json.dumps({"error": f"Not a directory: {path}"})

            entries = []
            for item in sorted(target.iterdir()):
                entry = {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                }
                if item.is_file():
                    entry["size_bytes"] = item.stat().st_size
                entries.append(entry)

            return json.dumps({"path": str(target), "entries": entries[:100]})  # Max 100 entries
        except Exception as e:
            return json.dumps({"error": str(e)})

    def create_directory(self, path: str) -> str:
        """Create a directory and any missing parent directories. Returns success status."""
        target = Path(path).resolve()

        if not self._permissions.can_write(target):
            return json.dumps({"error": f"Permission denied: cannot create {path} at current tier."})

        try:
            target.mkdir(parents=True, exist_ok=True)
            return json.dumps({"success": True, "path": str(target)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def web_request(self, url: str, method: str = "GET", headers: dict = None, body: str = "") -> str:
        """Make an HTTP request and return the response. Supports GET and POST. Returns status code and body text."""
        try:
            import httpx
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                if method.upper() == "GET":
                    resp = client.get(url, headers=headers)
                elif method.upper() == "POST":
                    resp = client.post(url, headers=headers, content=body)
                else:
                    return json.dumps({"error": f"Unsupported method: {method}"})

                # Truncate large responses
                body_text = resp.text[:10000] if resp.text else ""
                return json.dumps({
                    "status_code": resp.status_code,
                    "body": body_text,
                    "headers": dict(resp.headers),
                })
        except ImportError:
            return json.dumps({"error": "httpx not installed. Run: pip install httpx"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def download_file(self, url: str, filename: str = "") -> str:
        """Download a file from a URL to the workspace downloads directory. Returns the saved file path."""
        try:
            import httpx

            DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

            if not filename:
                filename = url.split("/")[-1].split("?")[0] or "download"

            dest = DOWNLOADS_DIR / filename

            with httpx.Client(timeout=60, follow_redirects=True) as client:
                with client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    with open(dest, "wb") as f:
                        for chunk in resp.iter_bytes(8192):
                            f.write(chunk)

            return json.dumps({"success": True, "path": str(dest), "size_bytes": dest.stat().st_size})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def system_info(self) -> str:
        """Get system information: OS, CPU, RAM, disk, and running process count."""
        try:
            info = {
                "os": platform.platform(),
                "architecture": platform.machine(),
                "python": platform.python_version(),
                "cpu_count": os.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=0.5),
                "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
                "ram_used_percent": psutil.virtual_memory().percent,
                "disk_usage": {},
                "process_count": len(psutil.pids()),
            }

            # Disk usage for key partitions
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    info["disk_usage"][part.mountpoint] = {
                        "total_gb": round(usage.total / (1024**3), 1),
                        "used_percent": usage.percent,
                    }
                except Exception:
                    pass

            return json.dumps(info)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def search_files(self, pattern: str, directory: str = "", recursive: bool = True) -> str:
        """Search for files matching a glob pattern in a directory. Returns matching file paths."""
        search_dir = Path(directory or str(WORKSPACE_DIR)).resolve()

        if not self._permissions.can_read(search_dir):
            return json.dumps({"error": f"Permission denied: cannot search {directory} at current tier."})

        try:
            if recursive:
                matches = list(search_dir.rglob(pattern))
            else:
                matches = list(search_dir.glob(pattern))

            results = [str(m) for m in matches[:50]]  # Max 50 results
            return json.dumps({"pattern": pattern, "directory": str(search_dir), "matches": results})
        except Exception as e:
            return json.dumps({"error": str(e)})
