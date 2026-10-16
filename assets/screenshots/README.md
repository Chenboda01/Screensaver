# Gallery captures

From the repository root, run:

```bash
uv run tools/make_screenshots.py
```

Alternatively, use `python3 tools/make_screenshots.py` with PyQt6 and Pillow installed. The script writes the WebP stills and GIFs in this directory. Its inline dependencies describe the capture environment; system fonts and Qt versions can affect text rasterization.

These are actual `Saver` widget renders through its production `paintEvent`, including Bob, scene effects, captions, and the BobOS interface. No screenshot is hand-drawn or AI-generated. The script uses Qt's offscreen platform and does not launch `start.sh`, request a lock, fetch weather, or read/write the user's saved settings or weather cache.

Reproducible inputs:

- Original theme stills: 1280×720 at five seconds after appearance, Live Sky off, particle seed 22, clock hidden.
- Live Sky: Mountains, Boston coordinates (42.36, −71.06), March 25, 2024. Sunrise 10:40 UTC, noon 16:45 UTC, sunset 23:00 UTC, full-moon night 03:00 UTC. Astronomy is calculated by `sky_position`.
- Rain: noon with a fixed sample (weather code 63, cloud cover 85%, precipitation 4 mm, wind 12 km/h, temperature 9 °C), rendered through the ordinary weather effects.
- Hero GIF: moonlit Mountains, six seconds at 10 fps, 768×432.
- BobOS: the existing accelerated preview timeline; home-screen still at nine seconds, GIF from six through twelve seconds (zoom, home, browser). Its fictional clock is fixed at 19:30.

Random selects one of the five themes, so it has no separate screenshot. These gallery assets illustrate the application and are not a new release. Keep the combined image files below 10 MB when regenerating.
