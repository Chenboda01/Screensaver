from PyQt6.QtCore import QDateTime, QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from bobos import BobOSPhase, BobOSStatus


class PhoneFrameRenderer:
    def draw_phone_zoom(self, p: QPainter, w: int, h: int, status: BobOSStatus, t: float) -> None:
        """Ease the camera from Bob's phone into its landscape OS display."""
        duration = self.phase_duration(status.phase)
        progress = min(1.0, status.phase_elapsed_seconds / duration)
        if status.phase is BobOSPhase.ZOOM_OUT:
            progress = 1.0 - progress
        eased = progress*progress*(3.0 - 2.0*progress)
        scale = min(w/1250, h/800, 1.35)
        small = QRectF(w*.5 + 60*scale, h*.56 - 72*scale, 110*scale, 70*scale)
        large = QRectF(w*.045, h*.035, w*.91, h*.93)
        frame = QRectF(
            small.x() + (large.x()-small.x())*eased,
            small.y() + (large.y()-small.y())*eased,
            small.width() + (large.width()-small.width())*eased,
            small.height() + (large.height()-small.height())*eased,
        )
        screen_phase = BobOSPhase.HOME if status.phase is BobOSPhase.ZOOM_IN else BobOSPhase.SHUTDOWN
        self.draw_phone_canvas(p, frame, BobOSStatus(screen_phase, status.phase_elapsed_seconds), t)

    def phase_duration(self, phase: BobOSPhase) -> float:
        """Return the configured length for a transition phase."""
        durations = dict(self.bobos_timeline.adventure_sequence)
        return float(durations.get(phase, 1))

    def draw_phone_os(self, p: QPainter, w: int, h: int, status: BobOSStatus, t: float) -> None:
        """Draw the complete simulated BobOS mobile interface."""
        self.draw_phone_canvas(p, QRectF(w*.045, h*.035, w*.91, h*.93), status, t)

    def draw_phone_canvas(self, p: QPainter, frame: QRectF, status: BobOSStatus, t: float) -> None:
        """Render a fictional phone shell, status bar, and animated application."""
        p.save()
        p.translate(frame.topLeft())
        p.scale(frame.width()/900, frame.height()/520)
        p.setPen(QPen(QColor('#87eaff'), 5))
        p.setBrush(QColor('#050a17'))
        p.drawRoundedRect(QRectF(0, 0, 900, 520), 38, 38)
        screen = QRectF(17, 14, 866, 492)
        p.setClipRect(screen)
        background = QLinearGradient(0, 14, 0, 506)
        background.setColorAt(0, QColor('#121d3b'))
        background.setColorAt(1, QColor('#091226'))
        p.fillRect(screen, background)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#080f20'))
        p.drawRect(QRectF(17, 14, 866, 40))
        p.setPen(QColor('#e8f6ff'))
        p.setFont(QFont('Sans Serif', 16, QFont.Weight.DemiBold))
        p.drawText(QRectF(35, 17, 85, 30), Qt.AlignmentFlag.AlignVCenter, QDateTime.currentDateTime().toString('h:mm'))
        p.setFont(QFont('Sans Serif', 13))
        p.drawText(QRectF(650, 17, 165, 30), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, 'AI Wi-Fi  ·  98%')
        p.setPen(QPen(QColor('#dcecff'), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(831, 25, 26, 13), 3, 3)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#66e6a4'))
        p.drawRect(QRectF(834, 28, 19, 7))

        if status.phase is BobOSPhase.HOME:
            self.draw_home_screen(p, t)
        elif status.phase is BobOSPhase.BROWSER:
            self.draw_browser(p, status.phase_elapsed_seconds, t)
        elif status.phase is BobOSPhase.NOTIFICATION:
            self.draw_notification_center(p, status.phase_elapsed_seconds, t)
        elif status.phase is BobOSPhase.FILES:
            self.draw_files(p, status.phase_elapsed_seconds, t)
        elif status.phase is BobOSPhase.TERMINAL:
            self.draw_terminal(p, status.phase_elapsed_seconds, t)
        elif status.phase is BobOSPhase.GAMES:
            self.draw_games(p, status.phase_elapsed_seconds, t)
        elif status.phase is BobOSPhase.SETTINGS:
            self.draw_phone_settings(p, status.phase_elapsed_seconds, t)
        elif status.phase is BobOSPhase.CHAT:
            self.draw_chat(p, status.phase_elapsed_seconds, t)
        elif status.phase is BobOSPhase.MAPS:
            self.draw_maps(p, status.phase_elapsed_seconds, t)
        elif status.phase is BobOSPhase.WEATHER:
            self.draw_phone_weather(p, status.phase_elapsed_seconds, t)
        elif status.phase is BobOSPhase.CALENDAR:
            self.draw_calendar(p, status.phase_elapsed_seconds, t)
        elif status.phase is BobOSPhase.APP_STORE:
            self.draw_app_store(p, status.phase_elapsed_seconds, t)
        elif status.phase is BobOSPhase.CAMERA:
            self.draw_camera(p, status.phase_elapsed_seconds, t)
        elif status.phase is BobOSPhase.PET:
            self.draw_pet(p, status.phase_elapsed_seconds, t)
        else:
            p.fillRect(screen, QColor(3, 6, 15, min(235, int(status.phase_elapsed_seconds*40))))
            p.setPen(QColor('#aeefff'))
            p.setFont(QFont('Sans Serif', 34, QFont.Weight.Bold))
            p.drawText(QRectF(80, 205, 740, 72), Qt.AlignmentFlag.AlignCenter, 'BobOS is powering down')
            p.setFont(QFont('Sans Serif', 18))
            p.drawText(QRectF(80, 280, 740, 45), Qt.AlignmentFlag.AlignCenter, 'Saving Bob’s imaginary high score…')
        p.restore()

    @staticmethod
    def draw_phone_header(p: QPainter, title: str, subtitle: str = '') -> None:
        p.setPen(QColor('#87eaff'))
        p.setFont(QFont('Sans Serif', 17, QFont.Weight.Bold))
        p.drawText(QRectF(38, 66, 200, 38), Qt.AlignmentFlag.AlignVCenter, '‹  Home')
        p.setPen(QColor('#f0f8ff'))
        p.setFont(QFont('Sans Serif', 24, QFont.Weight.Bold))
        p.drawText(QRectF(240, 60, 600, 42), Qt.AlignmentFlag.AlignCenter, title)
        if subtitle:
            p.setPen(QColor('#9eb8d6'))
            p.setFont(QFont('Sans Serif', 14))
            p.drawText(QRectF(240, 100, 600, 28), Qt.AlignmentFlag.AlignCenter, subtitle)

    @staticmethod
    def draw_phone_avatar(p: QPainter, rect: QRectF, mood: str,
                          palette: dict[str, tuple[int, int, int]]) -> None:
        p.save()
        p.setPen(QPen(QColor(*palette['outline']), 2))
        p.setBrush(QColor(*palette['face']))
        p.drawRoundedRect(rect, rect.width()*.32, rect.width()*.32)
        eye_y = rect.y()+rect.height()*.44
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(*palette['eyes']))
        eye_size = rect.width()*.095
        p.drawEllipse(QPointF(rect.x()+rect.width()*.35, eye_y), eye_size, eye_size*1.3)
        p.drawEllipse(QPointF(rect.x()+rect.width()*.65, eye_y), eye_size, eye_size*1.3)
        p.setPen(QPen(QColor(*palette['eyes']), max(1, rect.width()*.035), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if mood == 'surprised':
            p.drawEllipse(QPointF(rect.center().x(), rect.y()+rect.height()*.68), eye_size*.7, eye_size)
        elif mood == 'confused':
            p.drawArc(QRectF(rect.x()+rect.width()*.38, rect.y()+rect.height()*.59,
                             rect.width()*.24, rect.height()*.2), 25*16, 125*16)
        else:
            p.drawArc(QRectF(rect.x()+rect.width()*.35, rect.y()+rect.height()*.58,
                             rect.width()*.3, rect.height()*.22), 190*16, 160*16)
        p.restore()

    def draw_bob_reaction(self, p: QPainter, t: float, mood: str) -> None:
        self.draw_phone_avatar(p, QRectF(804, 462, 42, 38), mood, self.bob_appearance.palette())

    @staticmethod
    def draw_toast(p: QPainter, title: str, message: str, opacity: float) -> None:
        p.save()
        p.setOpacity(opacity)
        p.setPen(QPen(QColor(143, 204, 243, 120), 1))
        p.setBrush(QColor(17, 34, 59, 245))
        p.drawRoundedRect(QRectF(275, 423, 440, 66), 16, 16)
        p.setPen(QColor('#79e3ff'))
        p.setFont(QFont('Sans Serif', 13, QFont.Weight.Bold))
        p.drawText(QRectF(294, 427, 390, 22), Qt.AlignmentFlag.AlignVCenter, title)
        p.setPen(QColor('#f0f6ff'))
        p.setFont(QFont('Sans Serif', 13))
        p.drawText(QRectF(294, 450, 390, 25), Qt.AlignmentFlag.AlignVCenter, message)
        p.restore()
