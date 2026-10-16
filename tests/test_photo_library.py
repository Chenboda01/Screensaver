"""Bounded, opt-in local photo discovery and decoding tests."""
from __future__ import annotations

import os
from pathlib import Path
import time
from unittest.mock import patch

from PIL import Image
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QApplication

from screenbot.photos import (
    EMPTY_LIBRARY_MESSAGE,
    MAX_DECODED_IMAGES,
    MAX_IMAGE_HEIGHT,
    MAX_IMAGE_WIDTH,
    PhotoLibrary,
    decode_photo,
    default_photo_folder,
    discover_photos,
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _wait_until(predicate, timeout: float = 3.0) -> None:
    app = _app()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.005)
    assert predicate(), 'asynchronous photo operation did not finish in time'


def _image(path: Path, color: str = 'navy') -> None:
    Image.new('RGB', (32, 20), color).save(path)


def test_discovery_defaults_to_pictures_but_does_not_touch_it() -> None:
    assert default_photo_folder() == Path.home() / 'Pictures'
    library = PhotoLibrary(enabled=False)
    assert library.folder == default_photo_folder()
    with patch('screenbot.photos.os.scandir') as scan:
        assert not library.start_scan()
        scan.assert_not_called()
    assert library.photos == []
    library.close()


def test_discovery_filters_extensions_hidden_entries_and_optional_subfolders(tmp_path: Path) -> None:
    _image(tmp_path / 'z.JPG')
    _image(tmp_path / 'A.png')
    (tmp_path / 'notes.txt').write_text('not a photo')
    hidden_dir = tmp_path / '.private'
    hidden_dir.mkdir()
    _image(hidden_dir / 'hidden.jpg')
    child = tmp_path / 'album'
    child.mkdir()
    _image(child / 'nested.webp')

    assert [item.name for item in discover_photos(tmp_path)] == ['A.png', 'z.JPG']
    assert [item.name for item in discover_photos(tmp_path, include_subfolders=True)] == [
        'A.png', 'nested.webp', 'z.JPG',
    ]


def test_discovery_orders_by_name_date_and_seeded_random(tmp_path: Path) -> None:
    paths = [tmp_path / name for name in ('c.jpg', 'a.jpg', 'b.jpg')]
    for index, path in enumerate(paths):
        _image(path)
        path.chmod(0o600)
        os.utime(path, (1000 + index, 1000 + index))

    assert [p.name for p in discover_photos(tmp_path, order='name')] == ['a.jpg', 'b.jpg', 'c.jpg']
    assert [p.name for p in discover_photos(tmp_path, order='date')] == ['b.jpg', 'a.jpg', 'c.jpg']
    first = discover_photos(tmp_path, order='random', random_seed=27)
    second = discover_photos(tmp_path, order='random', random_seed=27)
    assert first == second
    assert {p.name for p in first} == {'a.jpg', 'b.jpg', 'c.jpg'}


def test_missing_and_empty_folders_return_friendly_empty_result(tmp_path: Path) -> None:
    empty = tmp_path / 'empty'
    empty.mkdir()
    assert discover_photos(empty) == []
    assert discover_photos(tmp_path / 'missing') == []

    library = PhotoLibrary(empty, enabled=True)
    assert library.start_scan()
    _wait_until(lambda: library._scan_future is not None and library._scan_future.done())
    assert library.photos == []
    assert library.message == EMPTY_LIBRARY_MESSAGE
    library.close()


def test_five_thousand_photos_scan_off_thread_and_complete_quickly(tmp_path: Path) -> None:
    # Zero-byte image names are sufficient for measuring discovery; no image
    # payloads are read while the catalog is built.
    for index in range(5000):
        (tmp_path / f'photo-{index:04}.jpg').touch()

    library = PhotoLibrary(tmp_path, enabled=True)
    started = time.monotonic()
    assert library.start_scan()
    returned_in = time.monotonic() - started
    assert returned_in < 0.1
    _wait_until(lambda: library._scan_future is not None and library._scan_future.done())
    assert len(library.photos) == 5000
    assert time.monotonic() - started < 1.0
    library.close()


def test_exif_rotated_phone_photo_is_returned_upright(tmp_path: Path) -> None:
    path = tmp_path / 'phone.jpg'
    image = Image.new('RGB', (40, 20), 'white')
    for x in range(0, 20):
        for y in range(20):
            image.putpixel((x, y), (255, 0, 0))
    exif = Image.Exif()
    exif[274] = 6  # rotate 90 degrees clockwise for display
    image.save(path, exif=exif)

    decoded = decode_photo(path, QSize(100, 100))
    assert (decoded.width(), decoded.height()) == (20, 40)
    # The left half of the source becomes the top half after EXIF rotation.
    assert decoded.pixelColor(10, 5).red() > 200
    assert decoded.pixelColor(10, 35).green() > 200


def test_photo_library_bounds_decoded_cache_and_output_dimensions(tmp_path: Path) -> None:
    paths = []
    for index in range(5):
        path = tmp_path / f'{index}.png'
        Image.new('RGB', (5000, 3000), (index * 30, 10, 20)).save(path)
        paths.append(path)

    _app()
    library = PhotoLibrary(tmp_path, enabled=True)
    for path in paths:
        _wait_until(lambda: library.pending_decode_count < 2)
        assert library.request_photo(path, QSize(5000, 3000))
        _wait_until(lambda p=path: any(key.path == str(p) for key in library._cache))
    assert library.cached_image_count <= MAX_DECODED_IMAGES
    assert library.cached_image_count == MAX_DECODED_IMAGES
    for image in library._cache.values():
        assert image.width() <= MAX_IMAGE_WIDTH
        assert image.height() <= MAX_IMAGE_HEIGHT
    library.close()


def test_decode_rejects_paths_outside_folder_hidden_files_and_non_images(tmp_path: Path) -> None:
    root = tmp_path / 'photos'
    root.mkdir()
    outside = tmp_path / 'outside.png'
    _image(outside)
    hidden = root / '.secret.jpg'
    _image(hidden)
    note = root / 'note.txt'
    note.write_text('not an image')
    library = PhotoLibrary(root, enabled=True)
    assert not library.request_photo(outside, QSize(100, 100))
    assert not library.request_photo(hidden, QSize(100, 100))
    assert not library.request_photo(note, QSize(100, 100))
    assert library.cached_image_count == 0
    library.close()
