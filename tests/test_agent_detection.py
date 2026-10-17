import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import agent_prompt
import pytest
from screenbot import agent_detection


def test_stale_unfinished_codex_turn_is_inactive_even_if_session_file_was_touched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    session_file = tmp_path / ".codex" / "sessions" / "stale-session.jsonl"
    session_file.parent.mkdir(parents=True)
    records = [
        {
            "type": "event_msg",
            "timestamp": (now - timedelta(minutes=10)).isoformat(),
            "payload": {"type": "task_started", "turn_id": "stale-turn"},
        },
        {
            "type": "event_msg",
            "timestamp": now.isoformat(),
            "payload": {"type": "thread_settings_applied"},
        },
    ]
    session_file.write_text(
        "".join(json.dumps(record, separators=(",", ":")) + "\n" for record in records),
        encoding="utf-8",
    )
    monkeypatch.setattr(agent_detection.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(agent_detection.time, "time", lambda: now.timestamp())

    assert agent_detection._codex_turn_is_active() is False


def test_recent_unfinished_codex_turn_is_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    session_file = tmp_path / ".codex" / "sessions" / "active-session.jsonl"
    session_file.parent.mkdir(parents=True)
    session_file.write_text(
        json.dumps(
            {
                "type": "event_msg",
                "timestamp": now.isoformat(),
                "payload": {"type": "task_started", "turn_id": "active-turn"},
            },
            separators=(",", ":"),
        ) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(agent_detection.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(agent_detection.time, "time", lambda: now.timestamp())

    assert agent_detection._codex_turn_is_active() is True


def test_idle_codex_with_stale_turn_does_not_show_agent_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    session_file = tmp_path / ".codex" / "sessions" / "stale-session.jsonl"
    session_file.parent.mkdir(parents=True)
    session_file.write_text(
        "".join(
            json.dumps(record, separators=(",", ":")) + "\n"
            for record in [
                {
                    "type": "event_msg",
                    "timestamp": (now - timedelta(minutes=10)).isoformat(),
                    "payload": {"type": "task_started", "turn_id": "stale-turn"},
                },
                {
                    "type": "event_msg",
                    "timestamp": now.isoformat(),
                    "payload": {"type": "thread_settings_applied"},
                },
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(agent_detection.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(agent_detection.time, "time", lambda: now.timestamp())
    codex = agent_detection.Process(123, 1, "pts/0", "S", 600, "codex", "codex")

    with patch.object(agent_prompt, "_read_processes", return_value=[codex]), \
         patch.object(agent_prompt, "_is_agent_process", return_value=True), \
         patch.object(agent_prompt, "_cpu_ticks", return_value=100), \
         patch.object(agent_prompt.time, "sleep"), \
         patch.object(agent_prompt.sys, "argv", ["agent_prompt.py"]), \
         patch.object(agent_prompt, "user_wants_agent_in_background") as prompt:
        assert agent_prompt.main() == 0

    prompt.assert_not_called()
