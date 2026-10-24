"""Bring the local Zetaris stack back after a Docker Desktop restart.

After a restart the ``driver`` container often fails to start (``error mounting ... spark-defaults.conf: not a
directory``, exit 127) while ui, api and postgres come back by themselves. Recreating only the driver fixes it and keeps
the data (it lives in volumes). This module does what ``scripts/zetaris_up.sh`` does, so the UI can do it for you.

Set ``ZETARIS_DIR`` to the folder that holds Zetaris' docker-compose.yml (default: ~/Desktop/zetaris-platform).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable

from .tools_zetaris import ZetarisClient, ZetarisError


def compose_dir() -> Path:
    return Path(os.getenv("ZETARIS_DIR") or Path.home() / "Desktop" / "zetaris-platform")


def gateway_up() -> bool:
    try:
        ZetarisClient(timeout=6).query("SELECT 1 AS ok")
        return True
    except ZetarisError:
        return False


def _run(args: list[str], cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def heal(wait: int = 180, log: Callable[[str], None] = lambda _: None) -> str:
    """Returns: already-up | recovered | docker-missing | docker-not-running | no-compose-dir | timeout."""
    if gateway_up():
        return "already-up"
    if not shutil.which("docker"):
        return "docker-missing"
    folder = compose_dir()
    if not (folder / "docker-compose.yml").exists():
        return "no-compose-dir"
    if _run(["docker", "info"], folder, 30).returncode != 0:
        return "docker-not-running"
    log("starting the Zetaris containers")
    _run(["docker", "compose", "up", "-d"], folder)
    cid = _run(["docker", "compose", "ps", "-aq", "driver"], folder).stdout.strip()
    state = _run(["docker", "inspect", "-f", "{{.State.Status}}", cid], folder).stdout.strip() if cid else ""
    if state != "running":
        log("recreating the driver container (stale bind mount)")
        _run(["docker", "compose", "up", "-d", "--force-recreate", "--no-deps", "driver"], folder)
        cid = _run(["docker", "compose", "ps", "-aq", "driver"], folder).stdout.strip()
    deadline = time.time() + wait
    while time.time() < deadline:
        health = _run(["docker", "inspect", "-f", "{{.State.Health.Status}}", cid], folder).stdout.strip() if cid else ""
        if health == "healthy" and gateway_up():
            return "recovered"
        time.sleep(5)
    return "timeout"
