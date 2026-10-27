"""Local synthetic fixtures for review tooling. These are NOT board logs/results."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


capture = module("capture", "tools/stage5_board_capture.py")
bundle = module("bundle", "tools/stage5_prepare_board_bundle.py")

# Fabricated unit-test input only; never written to reports/stage5_01_board.
FIXTURE = """VAD segments: 2
ASR recognized: 2
Audio queue dropped: 0
LLM accepted/completed/success/failed/rejected: 1/1/1/0/0
TTS accepted/completed/success/failed/rejected/empty: 2/2/2/0/0/0
VISION completed/success/failed: 1/1/0
PASS
"""


class ToolTests(unittest.TestCase):
    def test_accepts_consistent_fixture_only(self):
        self.assertTrue(capture.accepted(capture.parse_summary(FIXTURE), 0, "both", False, False, False))

    def test_rejects_sigint_even_if_last_output_says_pass(self):
        for code in (0, 130, -2):
            self.assertFalse(capture.accepted(capture.parse_summary(FIXTURE), code, "both", True, False, False))

    def test_rejects_timeout_or_forced_kill(self):
        summary = capture.parse_summary(FIXTURE)
        self.assertFalse(capture.accepted(summary, 0, "both", False, True, False))
        self.assertFalse(capture.accepted(summary, 0, "both", False, False, True))

    def test_rejects_pass_without_counts(self):
        self.assertFalse(capture.accepted(capture.parse_summary("PASS\n"), 0, "both", False, False, False))

    def test_rejects_missing_branch_or_dropped_audio(self):
        for text in (FIXTURE.replace("Audio queue dropped: 0", "Audio queue dropped: 1"),
                     FIXTURE.replace("VISION completed/success/failed: 1/1/0", "VISION completed/success/failed: 0/0/0")):
            self.assertFalse(capture.accepted(capture.parse_summary(text), 0, "both", False, False, False))

    def test_rejects_corrupted_counts_and_errors(self):
        for text in (FIXTURE.replace("1/1/1/0/0", "1"), FIXTURE + "[Fatal] fixture\n"):
            self.assertFalse(capture.accepted(capture.parse_summary(text), 0, "both", False, False, False))

    def test_source_bundle_excludes_models_and_binaries(self):
        selected = bundle.package_files(ROOT)
        self.assertIn(Path("src/audio/audio_worker.cpp"), selected)
        self.assertIn(Path("CMakeLists.txt"), selected)
        self.assertIn(Path("tools/stage5_board_build.sh"), selected)
        self.assertTrue(all(not p.is_absolute() and ".." not in p.parts for p in selected))
        self.assertFalse(any(p.parts[0] in {"models", "build", "backups"} or
                             p.suffix in {".onnx", ".rkllm", ".rknn", ".so", ".exe"} for p in selected))


if __name__ == "__main__":
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout, verbosity=2))
