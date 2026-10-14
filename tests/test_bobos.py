import configparser
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from screensaver import Saver

from bobos import (
    ADVENTURE_SECONDS,
    CONNECTION_SECONDS,
    MIN_COOLDOWN_SECONDS,
    PACK_UP_SECONDS,
    BobOSPhase,
    BobOSTimeline,
    bobos_may_run,
)


class BobOSTimelineTests(unittest.TestCase):
    def test_first_adventure_waits_until_delay_and_connection_phase(self) -> None:
        timeline = BobOSTimeline(activation_delay_seconds=60, show_connection_animation=True)

        self.assertEqual(timeline.phase_at(59.999), BobOSPhase.EXPLORING)
        self.assertEqual(timeline.phase_at(60), BobOSPhase.CONNECTING)
        self.assertEqual(timeline.phase_at(60 + CONNECTION_SECONDS), BobOSPhase.ACTIVE)

    def test_natural_first_offset_never_starts_before_the_selected_delay(self) -> None:
        timeline = BobOSTimeline(
            activation_delay_seconds=60,
            show_connection_animation=False,
            first_adventure_offset_seconds=90,
        )

        self.assertEqual(timeline.phase_at(149.999), BobOSPhase.EXPLORING)
        self.assertEqual(timeline.phase_at(150), BobOSPhase.ACTIVE)

    def test_disabled_connection_animation_enters_bobos_directly(self) -> None:
        timeline = BobOSTimeline(activation_delay_seconds=60, show_connection_animation=False)

        self.assertEqual(timeline.phase_at(60), BobOSPhase.ACTIVE)

    def test_adventure_closes_and_returns_to_exploring_for_full_cooldown(self) -> None:
        timeline = BobOSTimeline(
            activation_delay_seconds=60,
            show_connection_animation=False,
            cooldown_offset_seconds=0,
        )
        pack_up = 60 + ADVENTURE_SECONDS
        next_adventure = pack_up + PACK_UP_SECONDS + MIN_COOLDOWN_SECONDS

        self.assertEqual(timeline.phase_at(pack_up), BobOSPhase.PACKING_UP)
        self.assertEqual(timeline.phase_at(next_adventure - 0.001), BobOSPhase.EXPLORING)
        self.assertEqual(timeline.phase_at(next_adventure), BobOSPhase.ACTIVE)

    def test_disabled_features_keep_bob_exploring(self) -> None:
        timeline = BobOSTimeline(activation_delay_seconds=1, show_connection_animation=True)

        self.assertEqual(timeline.phase_at(100, enabled=False), BobOSPhase.EXPLORING)


class BobOSDependencyTests(unittest.TestCase):
    def test_disabling_backpack_blocks_bobos(self) -> None:
        self.assertFalse(
            bobos_may_run(
                backpack_enabled=False,
                bobos_enabled=True,
                password_lock_enabled=False,
                elapsed_seconds=600,
                lock_seconds=120,
            )
        )

    def test_disabling_bobos_leaves_backpack_available(self) -> None:
        self.assertFalse(
            bobos_may_run(
                backpack_enabled=True,
                bobos_enabled=False,
                password_lock_enabled=False,
                elapsed_seconds=600,
                lock_seconds=120,
            )
        )

    def test_real_lock_deadline_takes_priority(self) -> None:
        self.assertFalse(
            bobos_may_run(
                backpack_enabled=True,
                bobos_enabled=True,
                password_lock_enabled=True,
                elapsed_seconds=120,
                lock_seconds=120,
            )
        )

    def test_no_password_countdown_does_not_suppress_bobos(self) -> None:
        self.assertTrue(
            bobos_may_run(
                backpack_enabled=True,
                bobos_enabled=True,
                password_lock_enabled=False,
                elapsed_seconds=600,
                lock_seconds=120,
            )
        )


class SaverFeatureSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def make_saver(self, home: Path) -> Saver:
        with patch.object(Path, "home", return_value=home):
            return Saver()

    def write_settings(self, home: Path, **values: str) -> None:
        config = configparser.ConfigParser()
        config["Screensaver"] = values
        config_path = home / ".config" / "screenbot-screensaver.ini"
        config_path.parent.mkdir(parents=True)
        with config_path.open("w", encoding="utf-8") as config_file:
            config.write(config_file)

    def test_new_features_default_to_enabled_and_three_minutes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            saver = self.make_saver(Path(directory))
            self.addCleanup(saver.close)

            self.assertTrue(saver.ai_backpack_enabled)
            self.assertTrue(saver.bobos_enabled)
            self.assertEqual(saver.bobos_activation_delay_seconds, 180)
            self.assertTrue(saver.show_wifi_animation)

    def test_disabling_backpack_preserves_bobos_setting_but_suppresses_adventures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.write_settings(home, ai_backpack_enabled="false", bobos_enabled="true")
            saver = self.make_saver(home)
            self.addCleanup(saver.close)

            self.assertFalse(saver.ai_backpack_enabled)
            self.assertTrue(saver.bobos_enabled)
            self.assertEqual(saver.bobos_status(600).phase, BobOSPhase.EXPLORING)

    def test_disabling_bobos_keeps_backpack_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.write_settings(home, ai_backpack_enabled="true", bobos_enabled="false")
            saver = self.make_saver(home)
            self.addCleanup(saver.close)

            self.assertTrue(saver.ai_backpack_enabled)
            self.assertFalse(saver.bobos_enabled)
            self.assertEqual(saver.bobos_status(600).phase, BobOSPhase.EXPLORING)

    def test_activation_delay_is_clamped_to_one_through_thirty_minutes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.write_settings(home, bobos_activation_delay="45")
            saver = self.make_saver(home)
            self.addCleanup(saver.close)

            self.assertEqual(saver.bobos_activation_delay_seconds, 1800)

    def test_disabling_wifi_animation_skips_connecting_phase(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.write_settings(home, show_wifi_animation="false")
            saver = self.make_saver(home)
            self.addCleanup(saver.close)
            first_start = (
                saver.bobos_activation_delay_seconds
                + saver.bobos_timeline.first_adventure_offset_seconds
            )

            self.assertFalse(saver.show_wifi_animation)
            self.assertEqual(saver.bobos_status(first_start).phase, BobOSPhase.ACTIVE)


if __name__ == "__main__":
    unittest.main()
