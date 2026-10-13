#!/usr/bin/env python3
"""Ask before the screensaver covers a terminal running an AI agent."""
import os
import re
import shutil
import subprocess
import sys
from typing import Final


AGENT_COMMAND: Final[re.Pattern[str]] = re.compile(
    r"(?:^|[\s/])(?:codex|claude(?:-code)?|opencode|gemini|aider|goose|amp|cline|cursor-agent)(?=$|[\s.:/-])",
    re.IGNORECASE,
)


def terminal_agent_is_running() -> bool:
    """Return whether a recognized AI agent is attached to a terminal."""
    try:
        result = subprocess.run(
            ["ps", "-eo", "pid=,tty=,args="],
            capture_output=True,
            check=False,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False

    if result.returncode != 0:
        return False

    for line in result.stdout.splitlines():
        fields = line.strip().split(maxsplit=2)
        if len(fields) != 3:
            continue
        pid, terminal, command = fields
        if pid == str(os.getpid()) or terminal in ("?", "??"):
            continue
        if AGENT_COMMAND.search(command):
            return True
    return False


def user_wants_agent_in_background() -> bool:
    """Ask whether to keep the terminal agent running behind the saver."""
    notify_send = shutil.which("notify-send")
    if notify_send is None:
        print("ScreenBot: notify-send is unavailable; leaving the desktop visible.", file=sys.stderr)
        return False

    try:
        result = subprocess.run(
            [
                notify_send,
                "--wait",
                "--expire-time=0",
                "--action=keep=Yes",
                "--action=cancel=No",
                "--app-name=ScreenBot Screensaver",
                "ScreenBot Screensaver",
                "An AI agent is active in a terminal. Keep it working in the background while the screensaver starts?",
            ],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as error:
        print(f"ScreenBot: could not show the agent prompt: {error}", file=sys.stderr)
        return False

    return result.returncode == 0 and result.stdout.strip() == "keep"


def main() -> int:
    if not terminal_agent_is_running():
        return 0
    return 0 if user_wants_agent_in_background() else 1


if __name__ == "__main__":
    raise SystemExit(main())
