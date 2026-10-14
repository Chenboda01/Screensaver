import configparser
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from bobos import RELATIONSHIP_PHASES, BobOSPhase, BobOSStatus, BobOSTimeline
from screensaver import Saver


class BobOSRelationshipTimelineTests(unittest.TestCase):
    def test_relationship_story_is_optional_and_recurs_after_cooldown(self) -> None:
        without_story = BobOSTimeline(activation_delay_seconds=0, show_connection_animation=True)
        with_story = BobOSTimeline(
            activation_delay_seconds=0,
            show_connection_animation=True,
            relationship_story_enabled=True,
        )
        phases = tuple(phase for phase, _ in with_story.adventure_sequence)

        self.assertTrue(RELATIONSHIP_PHASES.isdisjoint(
            phase for phase, _ in without_story.adventure_sequence
        ))
        story_order = (
            BobOSPhase.DATE_MESSAGE, BobOSPhase.DATE_MAPS, BobOSPhase.DATE_WEATHER,
            BobOSPhase.DATE_CALENDAR, BobOSPhase.DATE_ADVICE, BobOSPhase.DATE_CONFIRM,
            BobOSPhase.GIRLFRIEND_CALL, BobOSPhase.DATE_MEET, BobOSPhase.DATE_FOLLOWUP,
        )
        positions = tuple(phases.index(phase) for phase in story_order)
        self.assertEqual(positions, tuple(sorted(positions)))
        date_message_offset = sum(
            duration
            for phase, duration in with_story.adventure_sequence
            if phases.index(phase) < phases.index(BobOSPhase.DATE_MESSAGE)
        )
        next_adventure = with_story.sequence_duration_seconds + with_story.cooldown_seconds
        self.assertEqual(with_story.phase_at(next_adventure + date_message_offset), BobOSPhase.DATE_MESSAGE)


class BobOSRelationshipRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    @staticmethod
    def write_config(home: Path, **values: str) -> None:
        config = configparser.ConfigParser()
        config["Screensaver"] = values
        config_path = home / ".config" / "screenbot-screensaver.ini"
        config_path.parent.mkdir(parents=True)
        with config_path.open("w", encoding="utf-8") as config_file:
            config.write(config_file)

    @staticmethod
    def make_saver(home: Path, **kwargs: bool) -> Saver:
        with patch.object(Path, "home", return_value=home):
            return Saver(**kwargs)

    def test_relationship_setting_defaults_on_and_can_be_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            enabled = self.make_saver(home)
            disabled = self.make_saver(home, preview_relationship_story=False)
            self.addCleanup(enabled.close)
            self.addCleanup(disabled.close)

            self.assertTrue(enabled.relationship_story_enabled)
            self.assertFalse(disabled.relationship_story_enabled)
            self.assertTrue(RELATIONSHIP_PHASES.isdisjoint(
                phase for phase, _ in disabled.bobos_timeline.adventure_sequence
            ))

    def test_saved_setting_can_disable_the_relationship_story(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.write_config(home, relationship_story_enabled="false")
            saver = self.make_saver(home)
            self.addCleanup(saver.close)

            self.assertFalse(saver.relationship_story_enabled)
            self.assertTrue(RELATIONSHIP_PHASES.isdisjoint(
                phase for phase, _ in saver.bobos_timeline.adventure_sequence
            ))

    def test_date_chat_animation_changes_as_bob_replies(self) -> None:
        def render(elapsed: float) -> QImage:
            image = QImage(900, 520, QImage.Format.Format_ARGB32)
            image.fill(0)
            painter = QPainter(image)
            saver.draw_phone_canvas(
                painter, QRectF(0, 0, 900, 520),
                BobOSStatus(BobOSPhase.DATE_MESSAGE, elapsed), elapsed,
            )
            painter.end()
            return image

        with tempfile.TemporaryDirectory() as directory:
            saver = self.make_saver(Path(directory), preview_bobos=True)
            self.addCleanup(saver.close)

            self.assertNotEqual(render(0.2), render(2.8))

    def test_date_scene_renders_in_every_existing_theme(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            saver = self.make_saver(Path(directory), preview_bobos=True, preview_relationship_story=True)
            self.addCleanup(saver.close)
            saver.resize(1280, 720)
            saver.password_lock = False
            saver.show_clock = False
            saver.show_timer = False
            date_elapsed = 0.0
            for phase, duration in saver.bobos_timeline.adventure_sequence:
                if phase is BobOSPhase.DATE_MEET:
                    date_elapsed += duration / 2
                    break
                date_elapsed += duration
            for theme in ("forest", "mountains", "space", "snow", "city"):
                saver.theme = theme
                saver.start_time = time.monotonic() - date_elapsed
                image = QImage(1280, 720, QImage.Format.Format_ARGB32)
                image.fill(0)
                painter = QPainter(image)
                saver.render(painter)
                painter.end()
                self.assertFalse(image.isNull(), theme)
