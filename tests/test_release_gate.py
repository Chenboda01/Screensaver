"""Execute the release gate against GitHub response scenarios without publishing."""
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('status,conclusion,expected', [
    ('completed', 'success', 0),
    ('completed', 'failure', 1),
    ('completed', 'cancelled', 1),
    ('in_progress', None, 1),
    ('queued', None, 1),
])
def test_release_gate_requires_completed_success(tmp_path: Path, status: str,
                                                conclusion: str | None, expected: int) -> None:
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    response = {'workflow_runs': [{'head_sha': sha, 'head_branch': 'main', 'event': 'push',
                                  'status': status, 'conclusion': conclusion,
                                  'created_at': '2026-10-17T00:00:00Z', 'id': 1}]}
    assert run_gate(tmp_path, response).returncode == expected


def run_gate(tmp_path: Path, response: dict) -> subprocess.CompletedProcess[str]:
    fake_gh = tmp_path / 'gh'
    fake_gh.write_text('#!/bin/sh\ncat "$GATE_RESPONSE"\n')
    fake_gh.chmod(0o755)
    data = tmp_path / 'response.json'
    data.write_text(json.dumps(response))
    env = {**os.environ, 'PATH': f'{tmp_path}:{os.environ["PATH"]}',
           'GATE_RESPONSE': str(data), 'GH_REPO': 'Chenboda01/Screensaver'}
    return subprocess.run(['bash', '.github/workflows/require-main-ci.sh'], cwd=ROOT,
                          env=env, capture_output=True, text=True, check=False)


def test_release_gate_rejects_missing_wrong_branch_or_older_success(tmp_path: Path) -> None:
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    good = {'head_sha': sha, 'head_branch': 'main', 'event': 'push', 'status': 'completed',
            'conclusion': 'success', 'created_at': '2026-10-17T00:00:00Z', 'id': 1}
    for runs in ([], [{**good, 'head_sha': 'other'}], [{**good, 'head_branch': 'feature'}],
                 [{**good, 'event': 'pull_request'}],
                 [good, {**good, 'id': 2, 'created_at': '2026-10-17T01:00:00Z',
                         'conclusion': 'failure'}]):
        result = run_gate(tmp_path, {'workflow_runs': runs})
        assert result.returncode != 0
        assert 'Release refused' in result.stderr
