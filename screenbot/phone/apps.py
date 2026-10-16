from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
import math
from bobos import BobOSPhase


class PhoneAppsRenderer:
    def draw_home_screen(self, p: QPainter, t: float) -> None:
        p.setPen(QColor('#f0f8ff'))
        p.setFont(QFont('Sans Serif', 26, QFont.Weight.Bold))
        p.drawText(QRectF(48, 65, 570, 45), Qt.AlignmentFlag.AlignVCenter, f'Good day, {self.bob_appearance.name}!')
        self.draw_phone_avatar(p, QRectF(795, 60, 54, 54), self.bob_mood(BobOSPhase.HOME, t), self.bob_appearance.palette())
        p.setPen(QColor('#9eb8d6'))
        p.setFont(QFont('Sans Serif', 15))
        p.drawText(QRectF(50, 109, 600, 30), Qt.AlignmentFlag.AlignVCenter, 'BobOS 2.0  ·  Your tiny world is ready')
        apps = (
            ('Bob Browser', '#54c9ef', 'B'), ('Bob Files', '#f3bd5b', 'F'), ('Bob Terminal', '#8be58f', '>_'),
            ('Bob Games', '#e58bf0', '★'), ('Bob Settings', '#8c9fff', '⚙'), ('BobChat', '#ed91bc', '♡'),
            ('Bob Maps', '#62c89c', 'M'), ('Bob Weather', '#85b9ed', '☼'), ('Bob Calendar', '#d5a5f4', 'C'),
            ('App Store', '#f2ad55', '↓'),
        )
        for index, (name, color, icon) in enumerate(apps):
            column, row = index % 3, index // 3
            rect = QRectF(47 + column*278, 145 + row*77, 250, 70)
            p.setPen(QPen(QColor(125, 187, 231, 80), 1))
            p.setBrush(QColor(28, 47, 78, 220))
            p.drawRoundedRect(rect, 16, 16)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(color))
            p.drawRoundedRect(QRectF(rect.x()+14, rect.y()+14, 42, 42), 12, 12)
            p.setPen(QColor('#081426'))
            p.setFont(QFont('Sans Serif', 17, QFont.Weight.Bold))
            p.drawText(QRectF(rect.x()+14, rect.y()+14, 42, 42), Qt.AlignmentFlag.AlignCenter, icon)
            p.setPen(QColor('#edf6ff'))
            p.setFont(QFont('Sans Serif', 15, QFont.Weight.DemiBold))
            p.drawText(QRectF(rect.x()+66, rect.y()+5, 174, 60), Qt.AlignmentFlag.AlignVCenter, name)

    def draw_browser(self, p: QPainter, elapsed: float, t: float) -> None:
        self.draw_phone_header(p, 'Bob Browser', 'bob://the-moon-is-cheeseish')
        p.setPen(QPen(QColor(116, 174, 220, 100), 1))
        p.setBrush(QColor('#142847'))
        p.drawRoundedRect(QRectF(42, 134, 816, 324), 18, 18)
        p.save()
        p.setClipRect(QRectF(50, 140, 800, 308))
        scroll = (elapsed*42) % 300
        p.setPen(QColor('#f0f8ff'))
        p.setFont(QFont('Sans Serif', 23, QFont.Weight.Bold))
        p.drawText(QRectF(70, 151-scroll, 760, 40), Qt.AlignmentFlag.AlignVCenter, 'A field guide to unusually friendly moons')
        p.setPen(QColor('#8edcf4'))
        p.setFont(QFont('Sans Serif', 15))
        p.drawText(QRectF(70, 194-scroll, 760, 30), Qt.AlignmentFlag.AlignVCenter, 'Bob’s completely fictional space journal')
        for index, text in enumerate((
            'Moon number one waves back at passing robots.',
            'Moon number two is mostly made of excellent snacks.',
            'Scientists agree: the moon is not made of cheese. Probably.',
            'Remember to pack a tiny umbrella for meteor showers.',
        )):
            y = 244 + index*57 - scroll
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(49, 82, 118, 185))
            p.drawRoundedRect(QRectF(68, y, 760, 46), 12, 12)
            p.setPen(QColor('#dcecff'))
            p.setFont(QFont('Sans Serif', 15))
            p.drawText(QRectF(87, y, 720, 46), Qt.AlignmentFlag.AlignVCenter, text)
        p.restore()
        self.draw_bob_reaction(p, t, 'curious')

    def draw_notification_center(self, p: QPainter, elapsed: float, t: float) -> None:
        self.draw_phone_header(p, 'Notifications', 'All caught up (except for these)')
        entries = (
            ('Bob Browser', 'A helpful webpage says to drink more starlight.', '#54c9ef'),
            ('Bob Games', 'A star says it is definitely not a potato.', '#e58bf0'),
            ('Weather', 'Chance of tiny fictional moonbeams: 100%.', '#70d9a8'),
        )
        for index, (title, message, color) in enumerate(entries):
            y = 142 + index*99 + math.sin(elapsed*2+index)*4
            p.setPen(QPen(QColor(130, 181, 224, 70), 1))
            p.setBrush(QColor('#172b49'))
            p.drawRoundedRect(QRectF(60, y, 780, 82), 18, 18)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(color))
            p.drawEllipse(QRectF(79, y+18, 42, 42))
            p.setPen(QColor('#f2f8ff'))
            p.setFont(QFont('Sans Serif', 16, QFont.Weight.Bold))
            p.drawText(QRectF(145, y+9, 650, 28), Qt.AlignmentFlag.AlignVCenter, title)
            p.setPen(QColor('#b7c9df'))
            p.setFont(QFont('Sans Serif', 14))
            p.drawText(QRectF(145, y+38, 650, 30), Qt.AlignmentFlag.AlignVCenter, message)
        self.draw_bob_reaction(p, t, 'surprised')

    def draw_files(self, p: QPainter, elapsed: float, t: float) -> None:
        self.draw_phone_header(p, 'Bob Files', 'Everything here is make-believe')
        files = (
            ('moon_photos.png', 'A picture of a moon waving', '#91b8ff'),
            ('snack_plan.txt', 'Three crumbs and a dream', '#ffd16e'),
            ('forest_map.fake', 'The tree with the friendly face', '#76e4a4'),
            ('important_notes.md', 'Do not feed the constellations', '#df9df0'),
            ('tiny_backup.zip', 'Compressed imaginary socks', '#78d9eb'),
        )
        selected = int(elapsed*1.4) % len(files)
        for index, (name, detail, color) in enumerate(files):
            y = 136 + index*62
            p.setPen(QPen(QColor(118, 177, 223, 45), 1))
            p.setBrush(QColor(32, 52, 83) if index == selected else QColor(20, 37, 65))
            p.drawRoundedRect(QRectF(58, y, 782, 54), 12, 12)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(color))
            p.drawRoundedRect(QRectF(74, y+10, 36, 34), 9, 9)
            p.setPen(QColor('#edf6ff'))
            p.setFont(QFont('Sans Serif', 15, QFont.Weight.DemiBold))
            p.drawText(QRectF(130, y+2, 380, 27), Qt.AlignmentFlag.AlignVCenter, name)
            p.setPen(QColor('#9eb4d1'))
            p.setFont(QFont('Sans Serif', 12))
            p.drawText(QRectF(130, y+26, 570, 22), Qt.AlignmentFlag.AlignVCenter, detail)
        self.draw_bob_reaction(p, t, 'happy')

    def draw_terminal(self, p: QPainter, elapsed: float, t: float) -> None:
        self.draw_phone_header(p, 'Bob Terminal', 'A pretend terminal that cannot run commands')
        p.setPen(QPen(QColor('#56d28e'), 2))
        p.setBrush(QColor('#07111d'))
        p.drawRoundedRect(QRectF(56, 134, 788, 322), 17, 17)
        lines = (
            ('bob@phone:~$ dance --moonwalk', 'A tiny moonwalk begins. No gravity harmed.'),
            ('bob@phone:~$ brew-sunshine', 'Brewing one imaginary cup of sunshine… done!'),
            ('bob@phone:~$ sudo pet-the-cat', 'Permission granted by the cat. Purrfect.'),
        )
        elapsed_characters = int(elapsed*13)
        for index, (command, output) in enumerate(lines):
            y = 160 + index*88
            command_start = index*88
            visible = max(0, min(len(command), elapsed_characters-command_start))
            p.setPen(QColor('#8fffb2'))
            p.setFont(QFont('Monospace', 15, QFont.Weight.DemiBold))
            p.drawText(QRectF(77, y, 745, 30), Qt.AlignmentFlag.AlignVCenter, command[:visible])
            if visible == len(command):
                p.setPen(QColor('#a9c1d8'))
                p.setFont(QFont('Monospace', 13))
                p.drawText(QRectF(91, y+34, 720, 26), Qt.AlignmentFlag.AlignVCenter, output)
        if int(elapsed*2) % 2 == 0:
            p.setPen(QPen(QColor('#91ffb6'), 2))
            p.drawLine(QPointF(78, 426), QPointF(91, 426))
        self.draw_bob_reaction(p, t, 'confused')

    def draw_games(self, p: QPainter, elapsed: float, t: float) -> None:
        self.draw_phone_header(p, 'Bob Games', 'Star Catch: a game with no winners or losers')
        field = QRectF(60, 138, 780, 300)
        p.setPen(QPen(QColor(125, 173, 224, 100), 1))
        p.setBrush(QColor('#101e3b'))
        p.drawRoundedRect(field, 20, 20)
        score = int(elapsed*1.7) % 100
        p.setPen(QColor('#f4f8ff'))
        p.setFont(QFont('Sans Serif', 19, QFont.Weight.Bold))
        p.drawText(QRectF(82, 151, 240, 35), Qt.AlignmentFlag.AlignVCenter, f'Star hugs: {score}')
        for index in range(8):
            x = 105 + ((index*137 + elapsed*65) % 690)
            y = 220 + math.sin(elapsed*2+index*1.4)*90
            size = 8 + (index % 3)*2
            p.setPen(QColor('#ffdf7c'))
            p.setFont(QFont('Sans Serif', 22))
            p.drawText(QRectF(x-size, y-size, size*2, size*2), Qt.AlignmentFlag.AlignCenter, '★')
        avatar_x = field.x()+field.width()*.5 + math.sin(elapsed*1.2)*200
        avatar_y = field.y()+field.height()*.72 + math.sin(elapsed*3)*14
        self.draw_phone_avatar(p, QRectF(avatar_x-24, avatar_y-24, 48, 48), self.bob_mood(BobOSPhase.GAMES, t), self.bob_appearance.palette())
        self.draw_bob_reaction(p, t, 'surprised')

    def draw_phone_settings(self, p: QPainter, elapsed: float, t: float) -> None:
        self.draw_phone_header(p, 'Bob Settings', 'These switches only change this drawing')
        rows = ('Starlight brightness', 'Extra snack reminders', 'Quiet moon mode', 'Automatic daydreams')
        for index, label in enumerate(rows):
            y = 149 + index*69
            p.setPen(QPen(QColor(125, 173, 224, 55), 1))
            p.setBrush(QColor('#172947'))
            p.drawRoundedRect(QRectF(70, y, 760, 57), 14, 14)
            p.setPen(QColor('#edf6ff'))
            p.setFont(QFont('Sans Serif', 16))
            p.drawText(QRectF(92, y+5, 500, 46), Qt.AlignmentFlag.AlignVCenter, label)
            enabled = ((int(elapsed*1.3)+index) % 3) != 0
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor('#42d8a0') if enabled else QColor('#54657d'))
            p.drawRoundedRect(QRectF(735, y+15, 64, 28), 14, 14)
            p.setBrush(QColor('#ffffff'))
            p.drawEllipse(QRectF(774 if enabled else 739, y+18, 22, 22))
        self.draw_bob_reaction(p, t, 'happy')

    def draw_chat(self, p: QPainter, elapsed: float, t: float) -> None:
        """Animate a self-contained, fictional BobChat group conversation."""
        self.draw_phone_header(p, 'BobChat', 'A pretend group chat · offline')
        messages = (
            ('Bob', 'Has anyone seen a meteor made of marshmallows?'),
            ('Orbit Club', 'That was your snack bag, Bob.'),
            ('Bob', 'Mystery solved. Deliciously.'),
        )
        for index, (sender, message) in enumerate(messages):
            y = 144 + index * 91
            visible = max(0, min(len(message), int((elapsed * 18) - index * 30)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor('#254c70') if sender == 'Bob' else QColor('#503b70'))
            p.drawRoundedRect(QRectF(95, y, 710, 72), 18, 18)
            p.setPen(QColor('#9edcf5'))
            p.setFont(QFont('Sans Serif', 13, QFont.Weight.Bold))
            p.drawText(QRectF(116, y + 7, 650, 22), Qt.AlignmentFlag.AlignVCenter, sender)
            p.setPen(QColor('#e7f8ff'))
            p.setFont(QFont('Sans Serif', 15))
            p.drawText(QRectF(116, y + 31, 660, 34), Qt.AlignmentFlag.AlignVCenter, message[:visible])
        self.draw_bob_reaction(p, t, 'happy')

    def draw_maps(self, p: QPainter, elapsed: float, t: float) -> None:
        """Show a pretend map of whimsical landmarks in Bob's world."""
        self.draw_phone_header(p, 'Bob Maps', 'Fictional places · no navigation data')
        p.setPen(QPen(QColor('#6da6c7'), 2))
        p.setBrush(QColor('#132c3d'))
        p.drawRoundedRect(QRectF(66, 137, 768, 312), 20, 20)
        for index in range(5):
            y = 176 + index * 49
            p.setPen(QPen(QColor('#31556a'), 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(104, y), QPointF(794, y + math.sin(index * 2.2) * 24))
        places = ('Cloud Café', 'Moon Crater 7', 'Glowtree Garden', 'Snowglobe Lookout')
        choice = places[min(len(places) - 1, int(elapsed / 3.0))]
        pin_x = 470 + math.sin(elapsed * 2.0) * 24
        p.setPen(QPen(QColor('#fff0a8'), 3))
        p.setBrush(QColor('#ffca68'))
        p.drawEllipse(QPointF(pin_x, 264), 17, 17)
        p.setPen(QColor('#f5f8ff'))
        p.setFont(QFont('Sans Serif', 19, QFont.Weight.Bold))
        p.drawText(QRectF(133, 363, 630, 40), Qt.AlignmentFlag.AlignCenter, choice)
        p.setPen(QColor('#b6cde0'))
        p.setFont(QFont('Sans Serif', 14))
        p.drawText(QRectF(133, 398, 630, 28), Qt.AlignmentFlag.AlignCenter,
                   'Bob zooms in, zooms out, and finds the snack district.')
        self.draw_bob_reaction(p, t, 'curious')

    def draw_phone_weather(self, p: QPainter, elapsed: float, t: float) -> None:
        """Draw a fictional forecast without using real weather data."""
        self.draw_phone_header(p, 'Bob Weather', 'Pretend forecast · no weather service')
        p.setPen(QPen(QColor(132, 187, 224, 90), 1))
        p.setBrush(QColor('#172d4b'))
        p.drawRoundedRect(QRectF(130, 142, 640, 280), 25, 25)
        pulse = 62 + math.sin(elapsed * 2) * 5
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#ffd98a'))
        p.drawEllipse(QPointF(450, 238), pulse, pulse)
        p.setPen(QColor('#f4f8ff'))
        p.setFont(QFont('Sans Serif', 27, QFont.Weight.Bold))
        p.drawText(QRectF(220, 310, 460, 44), Qt.AlignmentFlag.AlignCenter, 'Clear skies, 19°')
        p.setPen(QColor('#c8dbf0'))
        p.setFont(QFont('Sans Serif', 16))
        p.drawText(QRectF(190, 358, 520, 42), Qt.AlignmentFlag.AlignCenter,
                   'Forecast confidence: 100% imaginary')
        self.draw_bob_reaction(p, t, 'happy')

    def draw_calendar(self, p: QPainter, elapsed: float, t: float) -> None:
        """Animate Bob checking a fictional calendar of ordinary activities."""
        self.draw_phone_header(p, 'Bob Calendar', 'A pretend schedule · stored nowhere')
        entries = ('09:00 · Water the moon flowers', '12:30 · Snack break',
                   '18:00 · Watch the meteor shower')
        for index, entry in enumerate(entries):
            y = 155 + index * 82
            p.setPen(QPen(QColor(137, 180, 224, 80), 1))
            p.setBrush(QColor('#172a47'))
            p.drawRoundedRect(QRectF(115, y, 670, 64), 17, 17)
            p.setPen(QColor('#eef6ff'))
            p.setFont(QFont('Sans Serif', 17, QFont.Weight.DemiBold))
            p.drawText(QRectF(145, y + 7, 610, 50), Qt.AlignmentFlag.AlignVCenter, entry)
        self.draw_toast(p, 'Reminder', 'Snack break is approaching!', min(1.0, elapsed / 2.0))
        self.draw_bob_reaction(p, t, 'surprised')

    def draw_app_store(self, p: QPainter, elapsed: float, t: float) -> None:
        """Browse made-up BobOS apps without downloading or installing anything."""
        self.draw_phone_header(p, 'App Store', 'All apps are imaginary · nothing downloads')
        apps = (
            ('Cloud Counter', 'Count clouds drifting by', '#65bfe8'),
            ('Pixel Garden', 'Grow a tiny digital flower', '#72d59a'),
            ('Star Catch', 'Catch stars in a pretend game', '#d7a2ef'),
        )
        selected = int(elapsed / 4) % len(apps)
        for index, (name, description, color) in enumerate(apps):
            y = 145 + index * 96
            p.setPen(QPen(QColor(130, 181, 224, 80), 1))
            p.setBrush(QColor('#203c5e') if index == selected else QColor('#172b49'))
            p.drawRoundedRect(QRectF(84, y, 732, 78), 18, 18)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(color))
            p.drawRoundedRect(QRectF(103, y + 16, 46, 46), 14, 14)
            p.setPen(QColor('#f0f8ff'))
            p.setFont(QFont('Sans Serif', 16, QFont.Weight.Bold))
            p.drawText(QRectF(170, y + 7, 410, 30), Qt.AlignmentFlag.AlignVCenter, name)
            p.setPen(QColor('#b7c9df'))
            p.setFont(QFont('Sans Serif', 13))
            p.drawText(QRectF(170, y + 38, 430, 26), Qt.AlignmentFlag.AlignVCenter, description)
            p.setPen(QColor('#84efbd'))
            p.setFont(QFont('Sans Serif', 14, QFont.Weight.Bold))
            p.drawText(QRectF(618, y + 13, 160, 50), Qt.AlignmentFlag.AlignCenter, 'Preview')
        self.draw_bob_reaction(p, t, 'curious')
