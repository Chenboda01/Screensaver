"""Drawing-only Camera and Pet apps; all images are bounded and in memory."""
from dataclasses import dataclass
import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPen


@dataclass(slots=True)  # noqa: MUTABLE_OK
class CameraState:
    """Retain only the current low-resolution view and one simulated photo."""

    frame: QImage | None = None
    photo: QImage | None = None
    refresh_key: tuple[str, int] | None = None
    adventure_start: float | None = None
    captured: bool = False


class CameraPetRenderer:
    def draw_camera(self, p: QPainter, elapsed: float, t: float) -> None:
        """Reuse the real scenery cache in a small viewfinder, then take a selfie."""
        state = self.bobos_camera
        adventure_start = round(t - elapsed, 2)
        if state.adventure_start != adventure_start:
            state.adventure_start = adventure_start
            state.captured = False
            state.refresh_key = None
        key = (self.theme, -1 if self.reduce_motion else int(t * 5))
        if state.frame is None or (not state.captured and state.refresh_key != key):
            image = QImage(480, 200, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            layer = QPainter(image)
            layer.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            layer.scale(480 / self.width(), 200 / self.height())
            self.draw_scenery(layer, self.width(), self.height(), t)
            layer.end()
            portrait = QPainter(image)
            portrait.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            self.draw_phone_avatar(portrait, QRectF(194, 70, 92, 85), 'happy', self.bob_appearance.palette())
            portrait.end()
            state.frame = image
            state.refresh_key = key
        captured = elapsed >= 1.5
        if captured and not state.captured:
            state.photo = state.frame.copy()
            state.captured = True
        self.draw_phone_header(p, 'Bob Camera', 'A pretend selfie · no camera or files accessed')
        view = QRectF(90, 143, 720, 300)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.drawImage(view, state.photo if captured else state.frame)
        p.setPen(QPen(QColor('#d7fff8'), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(view, 12, 12)
        if not captured:
            p.drawRect(QRectF(366, 235, 168, 132))
        if not self.reduce_motion and 1.5 <= elapsed < 1.8:
            p.fillRect(view, QColor(255, 255, 255, round((1.8 - elapsed) / .3 * 220)))
        p.setPen(QColor('#ddfff5'))
        p.setFont(QFont('Sans Serif', 15))
        p.drawText(QRectF(90, 452, 700, 32), Qt.AlignmentFlag.AlignCenter,
                   'Selfie in Bob Files · kept only until screensaver closes' if captured else 'Hold still… say moon cheese!')
        self.draw_bob_reaction(p, t, 'happy')

    def draw_pet(self, p: QPainter, elapsed: float, t: float) -> None:
        """Animate a pixel pet receiving a snack and bouncing with its toy."""
        self.draw_phone_header(p, 'Bob Pet', 'Meet Pip · a tiny imaginary companion')
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#243f49'))
        p.drawRoundedRect(QRectF(85, 145, 730, 290), 20, 20)
        fed = elapsed >= 1.0
        playing = elapsed >= 2.0
        motion_time = 0.0 if self.reduce_motion else elapsed
        x = 410 + (math.sin(motion_time * 2) * 55 if playing else 0)
        y = 290 - (abs(math.sin(motion_time * 4)) * 28 if playing else 0)
        p.setBrush(QColor('#f2b58f'))
        p.drawRect(QRectF(x - 52, y - 44, 104, 80))
        p.drawRect(QRectF(x - 52, y - 68, 24, 24))
        p.drawRect(QRectF(x + 28, y - 68, 24, 24))
        p.drawRect(QRectF(x - 44, y + 36, 24, 16))
        p.drawRect(QRectF(x + 20, y + 36, 24, 16))
        p.setBrush(QColor('#152b3d'))
        p.drawRect(QRectF(x - 30, y - 18, 12, 12))
        p.drawRect(QRectF(x + 18, y - 18, 12, 12))
        p.drawRect(QRectF(x - 8, y + 8, 16, 8 if fed else 16))
        p.setBrush(QColor('#e5cf7e'))
        if not fed:
            p.drawEllipse(QPointF(580 - motion_time * 110, 300), 14, 10)
        p.setBrush(QColor('#8ae0ce'))
        p.drawRoundedRect(QRectF(540, 331, 80, 22), 8, 8)
        if playing:
            p.setBrush(QColor('#e7a3eb'))
            p.drawEllipse(QPointF(640 + math.sin(motion_time * 3) * 45,
                                  310 - abs(math.sin(motion_time * 3)) * 65), 22, 22)
        p.setPen(QColor('#f0f9f7'))
        p.setFont(QFont('Sans Serif', 18, QFont.Weight.DemiBold))
        message = 'Snack delivery!' if not fed else ('Playtime! Pip loves moonball.' if playing else 'Crunch! One happy pixel pet.')
        p.drawText(QRectF(105, 377, 690, 40), Qt.AlignmentFlag.AlignCenter, message)
        p.setPen(QColor('#adcfca'))
        p.setFont(QFont('Sans Serif', 14))
        p.drawText(QRectF(110, 451, 675, 32), Qt.AlignmentFlag.AlignCenter, 'Every visit is a fresh little adventure · no saved pet data')
        self.draw_bob_reaction(p, t, 'happy')
