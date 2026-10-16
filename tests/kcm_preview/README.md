# Preview integration check

This standalone Qt harness loads the compiled KCM, renders its real QML page,
clicks Preview, and launches the production Python preview through a thin capture
probe. It uses a temporary HOME and never installs files into the user's account.
The probe saves a frame and exits through the actual Qt key or mouse handler.

Build with the same Qt 6 / KDE Frameworks 6 development packages as the KCM,
plus Qt Test. Python 3 must have PyQt6.

```sh
cmake -S kcm -B build/kcm
cmake --build build/kcm
cmake -S tests/kcm_preview -B build/preview-test
cmake --build build/preview-test
mkdir -p .omo/evidence/preview-run
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  SCREENBOT_SOURCE="$PWD" \
  SCREENBOT_TEST_PYTHON="$(command -v python3)" \
  SCREENBOT_PREVIEW_EVIDENCE="$PWD/.omo/evidence/preview-run" \
  build/preview-test/preview_integration \
  "$PWD/build/kcm/bin/plasma/kcms/systemsettings/kcm_screenbot_screensaver.so"
```

Use a new evidence directory for every run (the launch receipt is append-only).
Set `QT_QPA_PLATFORM=wayland` to exercise the current desktop and display selection.
Set `SCREENBOT_PREVIEW_INPUT=mouse` to exit by movement instead of a key.
The harness returns nonzero for failed assertions or a preview that does not exit.

Run Python regression coverage with `python -m pytest tests/test_preview.py
 tests/test_bobos.py tests/test_live_sky.py tests/test_agent_prompt.py` in an
environment containing pytest and PyQt6. `SCREENBOT_PREVIEW_EVIDENCE` also enables
per-theme and fresh/stale-weather PNG captures in these tests.
