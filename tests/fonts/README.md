# Raster test fonts

DejaVu Sans regular and bold, version 2.37, copied without modification from the
Arch Linux `ttf-dejavu` package. Upstream: https://dejavu-fonts.github.io/.
The adjacent LICENSE contains the Bitstream Vera license and DejaVu public-domain
changes notice. Both weights are bundled so Qt need not synthesize machine-specific
bold text. `fonts.conf` limits Fontconfig discovery to this directory in pytest;
`conftest.py` also registers both fonts using `QFontDatabase.addApplicationFont`.
These files and environment settings are only used by tests.
