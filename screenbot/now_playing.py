"""A small plain-text media card, laid out beside the configured clock."""
from dataclasses import dataclass
from typing import Final

from PyQt6.QtCore import QRectF, QSizeF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen

from screenbot.mpris import NowPlaying, PAUSE_GRACE_SECONDS


@dataclass(frozen=True, slots=True)
class CardStyle:
    """Use the screensaver's existing dark overlay and clock text palette."""

    background: str = '#081323'
    foreground: str = '#ecf7ff'
    secondary: str = '#a9c1df'
    margin: int = 18
    gap: int = 12
    maximum_width: int = 360
    height: int = 84
    radius: int = 15


STYLE: Final = CardStyle()


def card_rect(screen: QSizeF, clock: QRectF | None, column: str, avoid: tuple[QRectF, ...] = ()) -> QRectF:
    """Keep the card near the clock, inside the display and clear of its text."""
    width = min(STYLE.maximum_width, max(0.0, screen.width() - STYLE.margin * 2))
    height = min(STYLE.height, max(0.0, screen.height() - STYLE.margin * 2))
    x = (screen.width() - width) / 2
    y = STYLE.margin
    if clock is not None:
        if column == 'left':
            x = clock.left()
        elif column == 'right':
            x = clock.right() - width
        else:
            x = clock.center().x() - width / 2
        y = clock.bottom() + STYLE.gap
        if clock.top() > screen.height() * .25 or y + height > screen.height() - STYLE.margin:
            y = clock.top() - STYLE.gap - height
    preferred = QRectF(max(STYLE.margin, min(x, screen.width() - width - STYLE.margin)),
                       max(STYLE.margin, min(y, screen.height() - height - STYLE.margin)), width, height)
    occupied = avoid + ((clock,) if clock is not None else ())
    candidates = [preferred]
    # Reserve Bob's whole motion range so the card does not chase his animation.
    candidates.extend(QRectF(candidate_x, candidate_y, width, height)
                      for candidate_y in (STYLE.margin, screen.height() - height - STYLE.margin)
                      for candidate_x in (preferred.x(), STYLE.margin, screen.width() - width - STYLE.margin))
    for candidate in candidates:
        if not any(candidate.intersects(region) for region in occupied):
            return candidate
    # Media is supplemental: omit it when the viewport has no clear full-size slot.
    return QRectF()


def card_opacity(snapshot: NowPlaying, now: float, reduce_motion: bool) -> float:
    """Fade for the final second of pause grace; reduced motion uses an instant hide."""
    if snapshot.track is None:
        return 0.0
    if snapshot.paused_at is None:
        return 1.0
    remaining = PAUSE_GRACE_SECONDS - max(0.0, now - snapshot.paused_at)
    return float(remaining > 0) if reduce_motion else max(0.0, min(1.0, remaining))


def paint_card(painter: QPainter, rect: QRectF, snapshot: NowPlaying) -> None:
    """Paint metadata as elided plain text; never interpret markup or fetch artwork."""
    track = snapshot.track
    if track is None or rect.width() < 100 or rect.height() < STYLE.height:
        return
    painter.save()
    painter.setPen(QPen(QColor(255, 255, 255, 35), 1))
    background = QColor(STYLE.background)
    background.setAlpha(238)
    painter.setBrush(background)
    painter.drawRoundedRect(rect, STYLE.radius, STYLE.radius)
    painter.setClipRect(rect.adjusted(8, 6, -8, -6))
    painter.setPen(QPen(QColor(STYLE.secondary), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    x, y = rect.left() + 20, rect.top() + 32
    painter.drawLine(round(x + 10), round(y - 5), round(x + 10), round(y + 16))
    painter.drawLine(round(x + 10), round(y - 5), round(x + 17), round(y - 2))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(STYLE.secondary))
    painter.drawEllipse(QRectF(x, y + 11, 10, 7))
    text_rect = QRectF(rect.left() + 52, rect.top() + 10, rect.width() - 66, 18)
    for value, size, bold, color, height in (
        (track.player, 10, False, STYLE.secondary, 18),
        (track.title, 14, True, STYLE.foreground, 24),
        (track.artist or track.album, 11, False, STYLE.secondary, 22),
    ):
        painter.setFont(QFont('Sans Serif', size, QFont.Weight.DemiBold if bold else QFont.Weight.Normal))
        painter.setPen(QColor(color))
        text_rect.setHeight(height)
        text = painter.fontMetrics().elidedText(value, Qt.TextElideMode.ElideRight, round(text_rect.width()))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        text_rect.translate(0, height)
    painter.restore()
