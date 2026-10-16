from PyQt6.QtCore import QDateTime, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter
import math
import math
from screenbot.burnin import burn_in_clock_drift


class ClockRenderer:
    def clock(self, p: QPainter, w: int, h: int, protection: str = 'off',
              elapsed_seconds: float = 0.0, scene_offset: tuple[float, float] = (0.0, 0.0),
              scene_scale: float = 1.0) -> None:
        columns = {
            'left': (w*.035, w*.42, Qt.AlignmentFlag.AlignLeft),
            'center': (w*.29, w*.42, Qt.AlignmentFlag.AlignHCenter),
            'right': (w*.545, w*.42, Qt.AlignmentFlag.AlignRight),
        }
        rows = {'top': h*.08, 'center': h*.38, 'bottom': h*.65}
        row, column = self.clock_position.split('-')
        x, width, horizontal_alignment = columns[column]
        y = rows[row]
        show_conditions = self.live_sky_enabled and self.live_sky_conditions and self.theme != 'space'
        drift_x, drift_y = burn_in_clock_drift(
            protection, elapsed_seconds, w, h, self.clock_position, self.clock_font_size,
            self.show_date, show_conditions, scene_offset, scene_scale)
        x += drift_x
        y += drift_y
        alignment = horizontal_alignment | Qt.AlignmentFlag.AlignVCenter
        date_y = y + self.clock_font_size * 1.5
        p.setPen(QColor('#ecf7ff'))
        p.setFont(QFont('Sans Serif', self.clock_font_size, QFont.Weight.DemiBold))
        time_format = 'HH:mm' if self.clock_format == '24h' else 'h:mm AP'
        p.drawText(QRectF(x, y, width, self.clock_font_size*1.5), alignment,
                   QDateTime.currentDateTime().toString(time_format))
        if self.show_date:
            p.setPen(QColor('#a9c1df'))
            p.setFont(QFont('Sans Serif', max(10, round(self.clock_font_size*.34))))
            p.drawText(QRectF(x, date_y, width, self.clock_font_size*.62), alignment,
                       QDateTime.currentDateTime().toString('ddd, MMM d'))
        if show_conditions:
            live = self.live_weather
            if not live.located:
                label = 'Location unavailable · choose a city in Settings'
            elif not live.fresh:
                label = 'Offline sky · weather unavailable'
            else:
                value = live.weather.temperature
                fahrenheit = self.live_sky_units == 'f'
                if fahrenheit:
                    value = value*9/5+32
                label = f"{value:.0f} °{'F' if fahrenheit else 'C'} · {live.weather.category}"
            p.setPen(QColor('#d9e8f5'))
            p.setFont(QFont('Sans Serif', max(10, round(self.clock_font_size*.3))))
            conditions_y = date_y + (self.clock_font_size*.62 if self.show_date else 0)
            p.drawText(QRectF(x, conditions_y, width, self.clock_font_size*.62), alignment, label)

    @staticmethod
    def countdown_color(progress):
        """Interpolate a continuously changing green-to-red countdown color.

        Stops: 0%=green, 25%=yellow, 50%=orange, 75%=red,
        then hold red for the final quarter. Works for every duration.
        """
        progress = max(0.0, min(1.0, progress))
        stops = [
            (0.00, (45, 230, 105)),
            (0.25, (252, 220, 43)),
            (0.50, (255, 138, 33)),
            (0.75, (255, 53, 70)),
            (1.00, (255, 53, 70)),
        ]
        for (at_a, ca), (at_b, cb) in zip(stops, stops[1:]):
            if progress <= at_b:
                blend = (progress - at_a) / (at_b - at_a)
                # Smoothstep eases transitions, with no sudden jumps.
                blend = blend * blend * (3.0 - 2.0 * blend)
                return QColor(*(round(a + (b - a)*blend) for a, b in zip(ca, cb)))
        return QColor(*stops[-1][1])

    def countdown(self, p, w, h, t):
        left = max(0, math.ceil(self.lock_seconds - t))
        label = (f"KDE locks in {left // 60:02d}:{left % 60:02d}"
                 if not self.lock_error else "Could not contact KDE screen locker — retrying")
        color = self.countdown_color(t / self.lock_seconds)
        p.save()
        p.setPen(color)
        p.setFont(QFont('Sans Serif', max(17, min(29, w//55)), QFont.Weight.Bold))
        p.drawText(QRectF(0, h * .86, w, 42), Qt.AlignmentFlag.AlignCenter, label)
        # Progress bar: the entire bar uses the same continuous color.
        bar_width = min(380, w*.46)
        bar_left = (w - bar_width) / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(215, 232, 255, 45))
        p.drawRoundedRect(QRectF(bar_left, h*.915, bar_width, 6), 3, 3)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(bar_left, h*.915, bar_width * max(0, 1-t/self.lock_seconds), 6), 3, 3)
        p.restore()
