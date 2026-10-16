"""Dynamic photo theme delegate (kept outside static-scene caching)."""
from PyQt6.QtGui import QPainter


def draw_background(scene, painter: QPainter, width: int, height: int, elapsed: float) -> None:
    scene.photo_slideshow.draw(painter, width, height, elapsed)
