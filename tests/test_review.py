import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shuilian-video-editor/scripts"))
from review_storyboard import read_cues, default_shots, build_html, validate_shots, embedded_image
from validate_srt import validate


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.cues = read_cues((ROOT / "examples/demo.srt").read_text())
        self.shots = default_shots(self.cues)

    def test_srt_timing_errors(self):
        self.assertFalse(validate("1\n00:00:02,000 --> 00:00:01,000\nbad")["structure_ok"])
        self.assertFalse(validate((ROOT / "examples/demo.srt").read_text(), 5)["structure_ok"])

    def test_missing_duplicate_reordered_cues_rejected(self):
        for shots in [self.shots[:-1], self.shots + [self.shots[0]], self.shots[::-1]]:
            with self.assertRaises(ValueError):
                validate_shots(shots, self.cues)

    def test_grouped_cues_keep_timing_and_escape_content(self):
        shots = copy.deepcopy(self.shots[1:])
        shots[0]["cue_ids"] = [1, 2]
        shots[0]["visual"] = '<script>alert("unsafe")</script>'
        html = build_html(self.cues, shots, ROOT / "examples")
        self.assertIn("0.000s — 5.800s", html)
        self.assertNotIn('<script>alert(', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn("非动画预览", html)

    def test_asset_boundary_and_signature(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(ValueError):
                embedded_image("../private.png", root)
            with self.assertRaises(ValueError):
                embedded_image(str(root / "absolute.png"), root)
            (root / "fake.png").write_text("not a PNG")
            with self.assertRaises(ValueError):
                embedded_image("fake.png", root)


if __name__ == "__main__":
    unittest.main()
