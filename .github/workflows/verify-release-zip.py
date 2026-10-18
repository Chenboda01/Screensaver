# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# How to run: python .github/workflows/verify-release-zip.py ARCHIVE.zip PREFIX/
from pathlib import Path, PurePosixPath
import subprocess
import sys
from zipfile import ZipFile
from typing import Final

MAX_BYTES: Final = 1_000_000
EXCLUDED: Final = (
    'tests/', 'assets/screenshots/', 'tools/', '.github/', '.omo/', 'releases/',
    'kcm/tests/', 'AGENTS.md', 'CONTRIBUTING.md',
)
RUNTIME_PATHS: Final = (
    ':(top,glob)*.py', ':(top,glob)*.sh', 'screenbot', 'kcm', 'assets/audio', 'facts',
    'countries_and_cities.txt', 'README.md', 'CHANGELOG.md', 'LICENSE',
    'assets/screenbot-icon.svg',
)


class ArchiveError(RuntimeError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def verify(archive: Path, prefix: str, source: Path) -> None:
    size = archive.stat().st_size
    if size >= MAX_BYTES:
        raise ArchiveError(f'ZIP must be under {MAX_BYTES} bytes; got {size}')
    tracked = subprocess.check_output(
        ['git', 'ls-files', '-z', '--', *RUNTIME_PATHS], cwd=source,
    ).decode().split('\0')
    required = {
        name for name in tracked if name and not name.startswith('kcm/tests/')
        and name not in ('kcm/DESIGN.md', 'kcm/Messages.sh')
    }
    with ZipFile(archive) as zipped:
        bad = zipped.testzip()
        if bad is not None:
            raise ArchiveError(f'Corrupt ZIP entry: {bad}')
        entries = {info.filename for info in zipped.infolist() if not info.is_dir()}
        for entry in entries:
            if not entry.startswith(prefix) or '..' in PurePosixPath(entry).parts:
                raise ArchiveError(f'Unexpected ZIP path: {entry}')
            relative = entry.removeprefix(prefix)
            if relative.startswith(EXCLUDED):
                raise ArchiveError(f'Developer content in ZIP: {relative}')
            if relative.endswith('.py'):
                compile(zipped.read(entry), relative, 'exec')
        for relative in sorted(required):
            entry = prefix + relative
            if entry not in entries:
                raise ArchiveError(f'Missing install source: {relative}')
            if zipped.read(entry) != (source / relative).read_bytes():
                raise ArchiveError(f'Archive differs from source: {relative}')
    print(f'PASS ZIP integrity, Python compilation, and {len(required)} source files; {size} bytes')


if __name__ == '__main__':
    verify(Path(sys.argv[1]), sys.argv[2], Path.cwd())
