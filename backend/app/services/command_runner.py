from __future__ import annotations

import subprocess
from pathlib import Path


class CommandExecutionError(Exception):
    pass


class CommandRunner:
    def run(self, command: list[str], cwd: Path | None = None, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                command,
                cwd=str(cwd) if cwd else None,
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise CommandExecutionError(f"Command not found: {command[0]}") from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            message = stderr or stdout or "Unknown subprocess error"
            raise CommandExecutionError(message) from exc
        except subprocess.TimeoutExpired as exc:
            raise CommandExecutionError(f"Command timed out after {timeout} seconds") from exc
