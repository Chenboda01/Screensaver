from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
import math
from bobos import BobOSPhase, BobOSStatus


class BobRenderer:
    def bob(self, p: QPainter, w: int, h: int, t: float, status: BobOSStatus,
            celebration_elapsed: float | None = None) -> None:
        """Paint Bob as a floating head with expressions driven by his phone use."""
        celebrating = celebration_elapsed is not None
        mood = 'happy' if celebrating else self.bob_mood(status.phase, t)
        pose_time = t
        if mood == 'sleepy':
            pose_time = t - (t % 32.0 - 22.0)
        x = w*.5 + math.sin(pose_time*.36)*min(w*.075, 85)
        y = h*.56 + math.sin(pose_time*1.45)*9
        scale = min(w/1250, h/800, 1.35)

        p.save()
        p.translate(x, y)
        p.scale(scale, scale)
        rotation = math.sin(pose_time*.72)*2.4
        if celebration_elapsed is not None:
            rotation += math.sin(celebration_elapsed*math.tau*.72)*13
        p.rotate(rotation)
        p.setPen(Qt.PenStyle.NoPen)
        halo = QRadialGradient(QPointF(0, 2), 185)
        halo.setColorAt(0, QColor(41, 212, 255, 78))
        halo.setColorAt(.55, QColor(41, 212, 255, 20))
        halo.setColorAt(1, QColor(41, 212, 255, 0))
        p.setBrush(halo)
        p.drawEllipse(QPointF(0, 0), 186, 186)
        p.setBrush(QColor(120, 220, 255, 28))
        p.drawEllipse(QPointF(0, 92), 34, 9)
        p.setPen(QPen(QColor('#66dfff'), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(0, -96, 0, -124)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#b2f9ff'))
        p.drawEllipse(QPointF(0, -130), 8, 8)
        p.setBrush(QColor('#1f5482'))
        p.drawRoundedRect(QRectF(-87, -28, 16, 42), 7, 7)
        p.drawRoundedRect(QRectF(71, -28, 16, 42), 7, 7)
        p.setPen(QPen(QColor('#73dcff'), 4))
        p.setBrush(QColor('#12355f'))
        p.drawRoundedRect(QRectF(-76, -96, 152, 144), 32, 32)
        if celebrating and celebration_elapsed is not None:
            confetti = ('#ffcf69', '#77e4a0', '#63d9ff', '#e89aff', '#ff8d88', '#fff1a6')
            p.setPen(Qt.PenStyle.NoPen)
            for index, color in enumerate(confetti):
                angle = index * math.tau / len(confetti) + celebration_elapsed * 1.8
                radius = 108 + 12 * math.sin(celebration_elapsed * 4.0 + index)
                p.setBrush(QColor(color))
                p.drawEllipse(QPointF(math.cos(angle) * radius,
                                      -24 + math.sin(angle) * radius), 4, 5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#081b3c'))
        p.drawRoundedRect(QRectF(-63, -76, 126, 102), 24, 24)
        p.setBrush(QColor(102, 217, 255, 26))
        p.drawRoundedRect(QRectF(-52, -68, 104, 20), 10, 10)

        eyes = QColor('#6bf6ff')
        blink = math.sin(t*1.55) > .988 or mood == 'sleepy'
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(eyes)
        if blink:
            p.setPen(QPen(eyes, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(-35, -22, -12, -22)
            p.drawLine(12, -22, 35, -22)
        elif mood == 'curious':
            p.drawEllipse(QPointF(-24, -18), 11, 16)
            p.drawEllipse(QPointF(24, -18), 11, 16)
        elif mood == 'surprised':
            p.drawEllipse(QPointF(-24, -18), 12, 17)
            p.drawEllipse(QPointF(24, -18), 12, 17)
        elif mood == 'happy':
            p.drawRoundedRect(QRectF(-39, -32, 28, 22), 10, 10)
            p.drawRoundedRect(QRectF(11, -32, 28, 22), 10, 10)
        else:
            p.drawRoundedRect(QRectF(-37, -30, 26, 20), 9, 9)
            p.drawRoundedRect(QRectF(11, -30, 26, 20), 9, 9)
        p.setPen(QPen(eyes, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if mood == 'curious':
            p.drawEllipse(QPointF(0, 6), 5, 7)
        elif mood == 'confused':
            p.drawArc(QRectF(-16, 4, 32, 18), 20*16, 140*16)
        elif mood == 'surprised':
            p.drawEllipse(QPointF(0, 8), 6, 8)
        elif mood == 'sleepy':
            p.drawLine(-11, 6, 11, 6)
        elif mood == 'happy':
            p.drawArc(QRectF(-20, -3, 40, 28), 190*16, 160*16)
        else:
            p.drawArc(QRectF(-16, 0, 32, 18), 180*16, 180*16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(107, 246, 255, 40))
        p.drawEllipse(QPointF(-44, 5), 5, 5)
        p.drawEllipse(QPointF(44, 5), 5, 5)
        if self.phone_enabled and status.phase in {
            BobOSPhase.EXPLORING,
            BobOSPhase.PHONE_ACTIVATION,
            BobOSPhase.WIFI_CONNECTING,
            BobOSPhase.BOOTING,
            BobOSPhase.RETURN,
        }:
            self.draw_small_phone(p, status, t)
        p.restore()

    @staticmethod
    def bob_mood(phase: BobOSPhase, t: float) -> str:
        """Choose a visible expression for the current fictional activity."""
        if phase in (BobOSPhase.CURIOUS, BobOSPhase.PHONE_ACTIVATION, BobOSPhase.WIFI_CONNECTING):
            return 'curious'
        if phase is BobOSPhase.TERMINAL:
            return 'confused' if int(t*2) % 3 == 0 else 'curious'
        if phase is BobOSPhase.GAMES:
            return 'surprised' if int(t*3) % 2 == 0 else 'happy'
        if phase in (BobOSPhase.BROWSER, BobOSPhase.FILES, BobOSPhase.SETTINGS, BobOSPhase.HOME):
            return 'happy' if int(t*1.4) % 4 else 'curious'
        if phase in (BobOSPhase.SHUTDOWN, BobOSPhase.ZOOM_OUT, BobOSPhase.RETURN):
            return 'happy'
        mood_cycle = t % 32.0
        if 10 <= mood_cycle < 15:
            return 'curious'
        if 15 <= mood_cycle < 22:
            return 'happy'
        if mood_cycle >= 22:
            return 'sleepy'
        return 'idle'

    @staticmethod
    def draw_small_phone(p: QPainter, status: BobOSStatus, t: float) -> None:
        """Show the phone powering on, joining fictional AI Wi-Fi, or booting."""
        p.save()
        p.setPen(QPen(QColor('#8beaff'), 3))
        p.setBrush(QColor('#0a1328'))
        p.drawRoundedRect(QRectF(73, -67, 110, 70), 13, 13)
        screen = QRectF(79, -61, 98, 58)
        p.setPen(Qt.PenStyle.NoPen)
        if status.phase in (BobOSPhase.EXPLORING, BobOSPhase.RETURN):
            p.setBrush(QColor('#091322'))
            p.drawRoundedRect(screen, 8, 8)
            p.setPen(QColor('#5dc9eb'))
            p.setFont(QFont('Sans Serif', 8, QFont.Weight.Bold))
            p.drawText(screen, Qt.AlignmentFlag.AlignCenter, 'BobOS')
        elif status.phase is BobOSPhase.PHONE_ACTIVATION:
            brightness = round(22 + 210*min(1.0, status.phase_elapsed_seconds / 2.0))
            p.setBrush(QColor(22, 64, 106, brightness))
            p.drawRoundedRect(screen, 8, 8)
        elif status.phase is BobOSPhase.WIFI_CONNECTING:
            p.setBrush(QColor('#102b42'))
            p.drawRoundedRect(screen, 8, 8)
            p.setPen(QColor('#c7f6ff'))
            p.setFont(QFont('Sans Serif', 9, QFont.Weight.Bold))
            p.drawText(QRectF(82, -57, 92, 20), Qt.AlignmentFlag.AlignCenter, 'AI Wi-Fi')
            progress = min(1.0, status.phase_elapsed_seconds / 8.0)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor('#4b6982'))
            p.drawRoundedRect(QRectF(89, -30, 78, 5), 2, 2)
            p.setBrush(QColor('#55e6ff'))
            p.drawRoundedRect(QRectF(89, -30, 78*progress, 5), 2, 2)
        else:
            p.setBrush(QColor('#13264a'))
            p.drawRoundedRect(screen, 8, 8)
            p.setPen(QColor('#e2f8ff'))
            p.setFont(QFont('Sans Serif', 9, QFont.Weight.Bold))
            p.drawText(QRectF(82, -56, 92, 18), Qt.AlignmentFlag.AlignCenter, 'BobOS 2.0')
            progress = min(1.0, status.phase_elapsed_seconds / 8.0)
            p.setPen(QPen(QColor('#62e8ff'), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(101, -21), QPointF(101 + 55*progress, -21))
        p.restore()

    def caption(self, p: QPainter, w: int, h: int, t: float, phase: BobOSPhase) -> None:
        """Keep the existing theme narration visible outside the phone close-up."""
        words = {
            'space': 'Bob is exploring the stars…',
            'mountains': 'Bob is exploring the mountains…',
            'snow': 'Bob is watching the snowfall…',
            'forest': 'Bob is exploring the forest…',
            'city': 'Bob is exploring the neon city…',
        }
        bobos_words = {
            BobOSPhase.CURIOUS: 'Bob spotted a new adventure!',
            BobOSPhase.PHONE_ACTIVATION: "Bob is waking up his phone…",
            BobOSPhase.WIFI_CONNECTING: 'Connecting to fictional AI Wi-Fi…',
            BobOSPhase.BOOTING: 'BobOS 2.0 is booting…',
            BobOSPhase.ZOOM_IN: 'Opening BobOS…',
            BobOSPhase.ZOOM_OUT: "Bob is putting away Bob's Phone…",
            BobOSPhase.RETURN: 'Bob is heading back to exploring…',
        }
        caption = bobos_words.get(phase, words[self.theme])
        p.setPen(QColor('#dcecff'))
        p.setFont(QFont('Sans Serif', max(13, min(22, w//72))))
        p.drawText(QRectF(0, h*.79, w, 39), Qt.AlignmentFlag.AlignCenter, caption)
        p.setPen(QColor('#92adc8'))
        p.setFont(QFont('Sans Serif', 12))
        p.drawText(QRectF(0, h-55, w, 30), Qt.AlignmentFlag.AlignCenter,
                   'Move the mouse or press a key to exit')
