# Development and releases

Run the same pinned Qt raster environment as CI:

```sh
uv run --python 3.13 --with pytest --with Pillow --with PyQt6==6.11.0 --with PyQt6-Qt6==6.11.0 python -m pytest tests
cmake -S kcm -B build
cmake --build build --parallel 2
```

Tests load the bundled DejaVu Sans regular/bold fonts and license in `tests/fonts/`.
The test fixture fixes logical DPI and font lookup; production keeps the system fonts.
The burn-in Off test compares two renders exactly, at the same timestamp and DPI.
Saved golden comparisons allow at most 0.5% changed pixels, with no channel changing
by more than 16/255. A moved element must fail. On failure, actual, expected, and
amplified difference PNGs are saved under `.omo/evidence/raster-failures/`; CI
uploads them with its Python test results. Inspect these before changing baselines.

For an intentional appearance or Qt upgrade, update both Qt pins in CI and this
command, regenerate once, review every changed image, then run without regeneration:

```sh
SCREENBOT_UPDATE_GOLDENS=1 uv run --python 3.13 --with pytest --with Pillow --with PyQt6==6.11.0 --with PyQt6-Qt6==6.11.0 python -m pytest tests/test_render_goldens.py
```

## Publishing a release

GitHub Releases is the source for downloadable ZIPs. Do not commit generated
release archives; `releases/*.zip` is ignored. The Release workflow creates the
ZIP from the tagged source and uploads it as a release asset.

1. Merge reviewed changes and the version description into `main`. Main requires
   `Python tests (offscreen, offline)` and `Qt 6 / KDE Frameworks 6 build`.
2. Wait for the **CI** push run for that exact commit on `main` to finish green.
3. Tag that commit with a new version such as `V24`, and push the tag:

   ```sh
   git tag -a V24 COMMIT_SHA -m 'ScreenBot Screensaver V24'
   git push origin V24
   ```

4. The **Release** workflow runs the same reusable Python and KCM jobs, checks the
   latest main CI run for the tagged commit again, builds and verifies the ZIP,
   then publishes the release with generated notes and its ZIP attachment.
   Missing, pending, failed, or cancelled main CI refuses publication. A failed
   test/build skips publication. Inspect Actions and fix the failure before
   rerunning; do not create a manual release to bypass these gates.

The ZIP contains the Python runtime, KDE settings sources and translations,
audio, facts, location data, installers, README, CHANGELOG, and license. Its
top-level folder matches the version. `.gitattributes` applies the same
`export-ignore` rules to local and CI archives: screenshots, tests, developer
tools, CI configuration, agent instructions, and historical ZIPs stay out.
Clone the repository when you need tests or developer tools; GitHub's automatic
source archives also honor `export-ignore`.

The package job refuses ZIPs at or above 1,000,000 bytes, checks integrity and
runtime source completeness, compiles every packaged Python file, and builds
and installs the extracted archive into an isolated account directory with
`install.sh --no-idle`. It renders the installed preview before publishing the
same verified artifact. Test a local archive from a clean commit with:

```sh
git archive --format=zip --prefix=ScreenBot-Screensaver-local/ --output=/tmp/screenbot-local.zip HEAD
python .github/workflows/verify-release-zip.py /tmp/screenbot-local.zip ScreenBot-Screensaver-local/
```

Repository administrators can technically bypass GitHub policy; keep branch
protection enabled and use the workflow for all releases.
