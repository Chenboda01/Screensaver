from pathlib import Path
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'ScreenBot-Screensaver-test/'
CHECK = ROOT / '.github/workflows/verify-release-zip.py'


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    result = tmp_path / 'release.zip'
    subprocess.run([
        'git', 'archive', '--worktree-attributes', '--format=zip',
        f'--prefix={PREFIX}', f'--output={result}', 'HEAD',
    ], cwd=ROOT, check=True)
    return result


def verify(archive: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CHECK), str(archive), PREFIX],
                          cwd=ROOT, capture_output=True, text=True, check=False)


def test_release_archive_preserves_install_sources_under_one_mb(archive: Path) -> None:
    result = verify(archive)
    assert result.returncode == 0, result.stderr
    assert 'PASS ZIP integrity' in result.stdout


@pytest.mark.parametrize('unwanted', [
    'tests/fixture.bin', 'assets/screenshots/gallery.gif', 'tools/dev.py',
    '.github/test.yml', '.omo/evidence.log', 'releases/old.zip',
])
def test_release_archive_rejects_developer_content(archive: Path, unwanted: str) -> None:
    with ZipFile(archive, 'a') as zipped:
        zipped.writestr(PREFIX + unwanted, 'unwanted')
    result = verify(archive)
    assert result.returncode != 0
    assert 'Developer content in ZIP' in result.stderr


def test_release_archive_rejects_missing_runtime_module(archive: Path, tmp_path: Path) -> None:
    incomplete = tmp_path / 'incomplete.zip'
    with ZipFile(archive) as original, ZipFile(incomplete, 'w', ZIP_DEFLATED) as modified:
        for entry in original.infolist():
            if entry.filename != PREFIX + 'screenbot/app.py':
                modified.writestr(entry, original.read(entry))
    result = verify(incomplete)
    assert result.returncode != 0
    assert 'Missing install source: screenbot/app.py' in result.stderr


def test_release_archive_rejects_one_mb_boundary(archive: Path) -> None:
    with archive.open('ab') as stream:
        stream.write(b'\0' * (1_000_000 - archive.stat().st_size))
    result = verify(archive)
    assert result.returncode != 0
    assert 'ZIP must be under 1000000 bytes; got 1000000' in result.stderr
