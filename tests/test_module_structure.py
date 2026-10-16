"""Protect the runtime's module boundaries and stable launcher facade."""
from pathlib import Path
import subprocess

from screenbot.app import Saver as RuntimeSaver
from screenbot.themes import THEME_RENDERERS
from screensaver import Saver as PublicSaver

ROOT = Path(__file__).parents[1]


def test_all_tracked_project_python_files_stay_below_the_400_line_limit() -> None:
    tracked = subprocess.run(
        ['git', 'ls-files', '-z', '--', '*.py'],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    modules = [ROOT / path.decode() for path in tracked.split(b'\0') if path]
    oversized = {
        str(path.relative_to(ROOT)): len(path.read_text(encoding='utf-8').splitlines())
        for path in modules
        if len(path.read_text(encoding='utf-8').splitlines()) > 400
    }
    assert not oversized, f'project Python files exceed 400 lines: {oversized}'
    assert {'agent_prompt.py', 'tests/test_module_structure.py'} <= {
        str(path.relative_to(ROOT)) for path in modules
    }, 'the project-wide check must include the prompt and tests'


def test_each_supported_theme_is_registered_in_its_own_module() -> None:
    assert set(THEME_RENDERERS) == {
        'space', 'mountains', 'snow', 'forest', 'city', 'aurora', 'ocean', 'desert', 'underwater'
    }
    assert all(callable(renderer) for renderer in THEME_RENDERERS.values())
    for theme in THEME_RENDERERS:
        assert (ROOT / 'screenbot' / 'themes' / f'{theme}.py').is_file()


def test_launcher_exports_the_runtime_saver_for_existing_callers() -> None:
    assert PublicSaver is RuntimeSaver
