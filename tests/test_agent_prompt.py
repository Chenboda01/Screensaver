import configparser
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agent_prompt


class AgentPolicyTests(unittest.TestCase):
    def test_manual_launch_bypasses_agent_detection(self) -> None:
        with patch.object(agent_prompt.sys, "argv", ["agent_prompt.py", "--manual"]):
            with patch.object(agent_prompt, "terminal_agent_status") as detect:
                self.assertEqual(agent_prompt.main(), 0)
        detect.assert_not_called()

    def test_uncertain_detection_cancels_even_when_always_start_is_saved(self) -> None:
        with patch.object(agent_prompt.sys, "argv", ["agent_prompt.py"]):
            with patch.object(agent_prompt, "terminal_agent_status", return_value=agent_prompt.DetectionResult.UNKNOWN):
                with patch.object(agent_prompt, "_read_mode", return_value=agent_prompt.AgentMode.ALWAYS_START) as read_mode:
                    self.assertEqual(agent_prompt.main(), 1)
        read_mode.assert_not_called()

    def test_process_scan_failure_is_reported_as_uncertain(self) -> None:
        with patch.object(agent_prompt, "_read_processes", return_value=None):
            self.assertEqual(agent_prompt.terminal_agent_status(), agent_prompt.DetectionResult.UNKNOWN)

    def test_idle_agent_with_no_work_or_cpu_growth_is_inactive(self) -> None:
        agent = agent_prompt.Process(10, 1, "pts/0", "S", 600, "codex", "codex")
        with patch.object(agent_prompt, "_read_processes", return_value=[agent]), \
             patch.object(agent_prompt, "_is_agent_process", return_value=True), \
             patch.object(agent_prompt, "_codex_turn_is_active", return_value=False), \
             patch.object(agent_prompt, "_cpu_ticks", return_value=100), \
             patch.object(agent_prompt.time, "sleep"):
            self.assertEqual(agent_prompt.terminal_agent_status(), agent_prompt.DetectionResult.INACTIVE)

    def test_agent_cpu_growth_is_active(self) -> None:
        agent = agent_prompt.Process(10, 1, "pts/0", "S", 600, "codex", "codex")
        with patch.object(agent_prompt, "_read_processes", return_value=[agent]), \
             patch.object(agent_prompt, "_is_agent_process", return_value=True), \
             patch.object(agent_prompt, "_codex_turn_is_active", return_value=False), \
             patch.object(agent_prompt, "_cpu_ticks", side_effect=[100, 10_000]), \
             patch.object(agent_prompt.time, "sleep"):
            self.assertEqual(agent_prompt.terminal_agent_status(), agent_prompt.DetectionResult.ACTIVE)

    def test_agent_cpu_read_failure_remains_uncertain(self) -> None:
        agent = agent_prompt.Process(10, 1, "pts/0", "S", 600, "codex", "codex")
        with patch.object(agent_prompt, "_read_processes", return_value=[agent]), \
             patch.object(agent_prompt, "_is_agent_process", return_value=True), \
             patch.object(agent_prompt, "_codex_turn_is_active", return_value=False), \
             patch.object(agent_prompt, "_cpu_ticks", return_value=None), \
             patch.object(agent_prompt.time, "sleep"):
            self.assertEqual(agent_prompt.terminal_agent_status(), agent_prompt.DetectionResult.UNKNOWN)

    def test_empty_process_scan_is_reported_as_inactive(self) -> None:
        with patch.object(agent_prompt, "_read_processes", return_value=[]):
            self.assertEqual(agent_prompt.terminal_agent_status(), agent_prompt.DetectionResult.INACTIVE)

    def test_inactive_agent_status_allows_normal_screensaver_start(self) -> None:
        with patch.object(agent_prompt.sys, "argv", ["agent_prompt.py"]):
            with patch.object(agent_prompt, "terminal_agent_status", return_value=agent_prompt.DetectionResult.INACTIVE):
                with patch.object(agent_prompt, "user_wants_agent_in_background") as prompt:
                    self.assertEqual(agent_prompt.main(), 0)
        prompt.assert_not_called()

    def test_saved_block_policy_cancels_only_when_detection_is_active(self) -> None:
        with patch.object(agent_prompt.sys, "argv", ["agent_prompt.py"]):
            with patch.object(agent_prompt, "terminal_agent_status", return_value=agent_prompt.DetectionResult.ACTIVE):
                with patch.object(agent_prompt, "_read_mode", return_value=agent_prompt.AgentMode.NEVER_START_WHILE_ACTIVE):
                    self.assertEqual(agent_prompt.main(), 1)

    def test_remembered_yes_persists_start_policy(self) -> None:
        choice = agent_prompt.PromptResult(start=True, remember=True)
        with patch.object(agent_prompt.sys, "argv", ["agent_prompt.py"]):
            with patch.object(agent_prompt, "terminal_agent_status", return_value=agent_prompt.DetectionResult.ACTIVE):
                with patch.object(agent_prompt, "_read_mode", return_value=agent_prompt.AgentMode.ALWAYS_ASK):
                    with patch.object(agent_prompt, "user_wants_agent_in_background", return_value=choice):
                        with patch.object(agent_prompt, "_save_mode") as save:
                            self.assertEqual(agent_prompt.main(), 0)
        save.assert_called_once_with(agent_prompt.AgentMode.ALWAYS_START)

    def test_remembered_no_persists_block_policy(self) -> None:
        choice = agent_prompt.PromptResult(start=False, remember=True)
        with patch.object(agent_prompt.sys, "argv", ["agent_prompt.py"]):
            with patch.object(agent_prompt, "terminal_agent_status", return_value=agent_prompt.DetectionResult.ACTIVE):
                with patch.object(agent_prompt, "_read_mode", return_value=agent_prompt.AgentMode.ALWAYS_ASK):
                    with patch.object(agent_prompt, "user_wants_agent_in_background", return_value=choice):
                        with patch.object(agent_prompt, "_save_mode") as save:
                            self.assertEqual(agent_prompt.main(), 1)
        save.assert_called_once_with(agent_prompt.AgentMode.NEVER_START_WHILE_ACTIVE)

    def test_timeout_answer_does_not_persist_a_choice(self) -> None:
        choice = agent_prompt.PromptResult(start=False, remember=False)
        with patch.object(agent_prompt.sys, "argv", ["agent_prompt.py"]):
            with patch.object(agent_prompt, "terminal_agent_status", return_value=agent_prompt.DetectionResult.ACTIVE):
                with patch.object(agent_prompt, "_read_mode", return_value=agent_prompt.AgentMode.ALWAYS_ASK):
                    with patch.object(agent_prompt, "user_wants_agent_in_background", return_value=choice):
                        with patch.object(agent_prompt, "_save_mode") as save:
                            self.assertEqual(agent_prompt.main(), 1)
        save.assert_not_called()

    def test_saved_mode_survives_a_config_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            config_file = Path(temp_directory) / "screenbot-screensaver.ini"
            config = configparser.ConfigParser()
            config.add_section("Screensaver")
            config.set("Screensaver", "theme", "space")
            with config_file.open("w", encoding="utf-8") as output:
                config.write(output)
            with patch.object(agent_prompt, "CONFIG_FILE", config_file):
                self.assertTrue(agent_prompt._save_mode(agent_prompt.AgentMode.NEVER_START_WHILE_ACTIVE))
                self.assertEqual(agent_prompt._read_mode(), agent_prompt.AgentMode.NEVER_START_WHILE_ACTIVE)
                saved = configparser.ConfigParser()
                saved.read(config_file)
                self.assertEqual(saved.get("Screensaver", "theme"), "space")


if __name__ == "__main__":
    unittest.main()
