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

from bobos import (
    MIN_COOLDOWN_SECONDS,
    NORMAL_SEQUENCE,
    PREVIEW_SEQUENCE,
    BobOSPhase,
    BobOSStatus,
    BobOSTimeline,
    bobos_may_run,
)
from screensaver import Saver


class BobOSTimelineTests(unittest.TestCase):
    def test_first_adventure_obeys_delay_and_all_phone_startup_transitions(self) -> None:
        timeline = BobOSTimeline(activation_delay_seconds=60, show_connection_animation=True)
        first_start = 60

        self.assertEqual(timeline.phase_at(first_start - 0.001), BobOSPhase.EXPLORING)
        self.assertEqual(timeline.phase_at(first_start), BobOSPhase.CURIOUS)
        self.assertEqual(timeline.phase_at(first_start + 4), BobOSPhase.PHONE_ACTIVATION)
        self.assertEqual(timeline.phase_at(first_start + 9), BobOSPhase.WIFI_CONNECTING)
        self.assertEqual(timeline.phase_at(first_start + 17), BobOSPhase.BOOTING)
        self.assertEqual(timeline.phase_at(first_start + 25), BobOSPhase.ZOOM_IN)
        self.assertEqual(timeline.phase_at(first_start + 30), BobOSPhase.HOME)

    def test_disabled_wifi_removes_only_the_wifi_phase(self) -> None:
        timeline = BobOSTimeline(activation_delay_seconds=60, show_connection_animation=False)
        phases = tuple(phase for phase, _ in timeline.adventure_sequence)

        self.assertNotIn(BobOSPhase.WIFI_CONNECTING, phases)
        self.assertIn(BobOSPhase.BOOTING, phases)
        self.assertEqual(timeline.phase_at(69), BobOSPhase.BOOTING)

    def test_first_adventure_never_starts_before_delay_plus_natural_offset(self) -> None:
        timeline = BobOSTimeline(
            activation_delay_seconds=60,
            show_connection_animation=True,
            first_adventure_offset_seconds=90,
        )

        self.assertEqual(timeline.phase_at(149.999), BobOSPhase.EXPLORING)
        self.assertEqual(timeline.phase_at(150), BobOSPhase.CURIOUS)

    def test_app_sequence_includes_all_fictional_app_interactions(self) -> None:
        timeline = BobOSTimeline(activation_delay_seconds=0, show_connection_animation=True)
        phases = tuple(phase for phase, _ in timeline.adventure_sequence)

        self.assertEqual(phases, tuple(phase for phase, _ in NORMAL_SEQUENCE))
        self.assertTrue({BobOSPhase.HOME, BobOSPhase.BROWSER, BobOSPhase.FILES,
                         BobOSPhase.TERMINAL, BobOSPhase.GAMES, BobOSPhase.SETTINGS}.issubset(phases))

    def test_adventure_shuts_down_returns_to_exploring_then_waits_full_cooldown(self) -> None:
        timeline = BobOSTimeline(activation_delay_seconds=30, show_connection_animation=True)
        first_end = 30 + timeline.sequence_duration_seconds
        next_start = first_end + MIN_COOLDOWN_SECONDS

        self.assertEqual(timeline.phase_at(first_end - 0.001), BobOSPhase.RETURN)
        self.assertEqual(timeline.phase_at(first_end), BobOSPhase.EXPLORING)
        self.assertEqual(timeline.phase_at(next_start - 0.001), BobOSPhase.EXPLORING)
        self.assertEqual(timeline.phase_at(next_start), BobOSPhase.CURIOUS)

    def test_preview_runs_entire_sequence_immediately_in_under_one_minute(self) -> None:
        timeline = BobOSTimeline(
            activation_delay_seconds=180,
            show_connection_animation=True,
            preview_mode=True,
        )

        self.assertEqual(tuple(phase for phase, _ in timeline.adventure_sequence),
                         tuple(phase for phase, _ in PREVIEW_SEQUENCE))
        self.assertLess(timeline.sequence_duration_seconds, 60)
        self.assertEqual(timeline.phase_at(0), BobOSPhase.CURIOUS)
        self.assertEqual(timeline.phase_at(timeline.sequence_duration_seconds), BobOSPhase.EXPLORING)

    def test_disabled_features_keep_bob_exploring(self) -> None:
        timeline = BobOSTimeline(activation_delay_seconds=0, show_connection_animation=True)

        self.assertEqual(timeline.phase_at(50, enabled=False), BobOSPhase.EXPLORING)


class BobOSLockAndSettingsTests(unittest.TestCase):
    def test_phone_disable_blocks_bobos(self) -> None:
        self.assertFalse(
            bobos_may_run(
                phone_enabled=False,
                bobos_enabled=True,
                password_lock_enabled=False,
                elapsed_seconds=600,
                lock_seconds=120,
            )
        )

    def test_bobos_disable_leaves_phone_setting_independent(self) -> None:
        self.assertFalse(
            bobos_may_run(
                phone_enabled=True,
                bobos_enabled=False,
                password_lock_enabled=False,
                elapsed_seconds=600,
                lock_seconds=120,
            )
        )

    def test_real_kde_lock_deadline_always_suppresses_bobos(self) -> None:
        self.assertFalse(
            bobos_may_run(
                phone_enabled=True,
                bobos_enabled=True,
                password_lock_enabled=True,
                elapsed_seconds=60,
                lock_seconds=60,
            )
        )

    def test_password_lock_disabled_does_not_suppress_bobos(self) -> None:
        self.assertTrue(
            bobos_may_run(
                phone_enabled=True,
                bobos_enabled=True,
                password_lock_enabled=False,
                elapsed_seconds=600,
                lock_seconds=120,
            )
        )


class SaverPreviewTests(unittest.TestCase):
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

    def make_saver(self, home: Path, **kwargs: bool) -> Saver:
        with patch.object(Path, "home", return_value=home):
            return Saver(**kwargs)

    def test_phone_and_bobos_default_on_and_delay_defaults_to_three_minutes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            saver = self.make_saver(Path(directory))
            self.addCleanup(saver.close)

            self.assertTrue(saver.phone_enabled)
            self.assertTrue(saver.bobos_enabled)
            self.assertEqual(saver.bobos_activation_delay_seconds, 180)
            self.assertTrue(saver.show_wifi_animation)

    def test_activation_clock_restarts_when_the_screensaver_is_shown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            saver = self.make_saver(Path(directory))
            self.addCleanup(saver.close)
            initial_start = saver.start_time

            saver.show()
            self.application.processEvents()

            self.assertGreaterEqual(saver.start_time, initial_start)
            self.assertEqual(saver.bobos_status(0).phase, BobOSPhase.EXPLORING)

    def test_v18_backpack_preference_migrates_to_phones_enabled_setting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.write_config(home, ai_backpack_enabled="false")
            saver = self.make_saver(home)
            self.addCleanup(saver.close)

            self.assertFalse(saver.phone_enabled)
            self.assertTrue(saver.bobos_enabled)
            self.assertEqual(saver.bobos_status(600).phase, BobOSPhase.EXPLORING)

    def test_phone_switch_persists_without_overwriting_bobos_preference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.write_config(home, bob_phone_enabled="false", bobos_enabled="true")
            saver = self.make_saver(home)
            self.addCleanup(saver.close)

            self.assertFalse(saver.phone_enabled)
            self.assertTrue(saver.bobos_enabled)
            self.assertEqual(saver.bobos_status(600).phase, BobOSPhase.EXPLORING)

    def test_preview_starts_immediately_but_still_obeys_configured_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.write_config(home, password_lock="true", lock_minutes="1")
            saver = self.make_saver(home, preview_bobos=True)
            self.addCleanup(saver.close)

            self.assertEqual(saver.bobos_status(0).phase, BobOSPhase.CURIOUS)
            self.assertTrue(saver.password_lock)
            self.assertEqual(saver.bobos_status(60).phase, BobOSPhase.EXPLORING)

    def test_preview_wifi_argument_overrides_the_saved_preference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.write_config(home, show_wifi_animation="false")

            with_wifi = self.make_saver(home, preview_bobos=True, preview_wifi_animation=True)
            without_wifi = self.make_saver(home, preview_bobos=True, preview_wifi_animation=False)
            self.addCleanup(with_wifi.close)
            self.addCleanup(without_wifi.close)

            self.assertTrue(with_wifi.show_wifi_animation)
            self.assertIn(BobOSPhase.WIFI_CONNECTING, with_wifi.bobos_timeline.phases)
            self.assertFalse(without_wifi.show_wifi_animation)
            self.assertNotIn(BobOSPhase.WIFI_CONNECTING, without_wifi.bobos_timeline.phases)

    def test_full_preview_sequence_renders_offscreen_frames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            saver = self.make_saver(Path(directory), preview_bobos=True)
            self.addCleanup(saver.close)
            saver.resize(1280, 720)
            saver.theme = "forest"
            saver.password_lock = False
            rendered_phases: list[BobOSPhase] = []
            elapsed = 0.0
            for phase, duration in saver.bobos_timeline.adventure_sequence:
                elapsed += duration / 2
                saver.start_time = time.monotonic() - elapsed
                status = saver.bobos_status(elapsed)
                self.assertEqual(status.phase, phase)
                image = QImage(1280, 720, QImage.Format.Format_ARGB32)
                image.fill(0)
                painter = QPainter(image)
                saver.render(painter)
                painter.end()
                self.assertFalse(image.isNull())
                rendered_phases.append(status.phase)
                elapsed += duration / 2

            self.assertEqual(tuple(rendered_phases), tuple(phase for phase, _ in PREVIEW_SEQUENCE))

    def test_browser_and_terminal_frames_change_as_bob_operates_the_phone(self) -> None:
        def render_phase(saver: Saver, phase: BobOSPhase, elapsed: float) -> QImage:
            image = QImage(900, 520, QImage.Format.Format_ARGB32)
            image.fill(0)
            painter = QPainter(image)
            saver.draw_phone_canvas(painter, QRectF(0, 0, 900, 520),
                                    BobOSStatus(phase, elapsed), 0)
            painter.end()
            return image

        with tempfile.TemporaryDirectory() as directory:
            saver = self.make_saver(Path(directory), preview_bobos=True)
            self.addCleanup(saver.close)

            self.assertNotEqual(
                render_phase(saver, BobOSPhase.BROWSER, 0.2),
                render_phase(saver, BobOSPhase.BROWSER, 3.8),
            )
            self.assertNotEqual(
                render_phase(saver, BobOSPhase.TERMINAL, 0.2),
                render_phase(saver, BobOSPhase.TERMINAL, 4.5),
            )


if __name__ == "__main__":
    unittest.main()
