import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from generate_short_script import storyboard, srt_text, srt_time, youtube_metadata


class ShortScriptTest(unittest.TestCase):
    def test_demo_disclosure(self):
        p = {"code": "1001", "name": "Orbit Dock", "tagline": "A cleaner desk",
             "features": ["fictional item"], "is_demo": True}
        result = storyboard(p)
        self.assertEqual(len(result["segments"]), 5)
        self.assertIn("Not a real product", result["segments"][2]["narration"])
        self.assertEqual(result["segments"][-1]["end_seconds"], 12.4)
        self.assertEqual(result["mode"], "template_without_ai")

    def test_real_captions_use_catalog_data_only(self):
        p = {"code": "1007", "name": "Approved Test Device",
             "tagline": "A tiny accessory", "features": ["USB-C port"],
             "is_demo": False}
        result = storyboard(p)
        joined = " ".join(x["narration"] for x in result["segments"])
        self.assertIn("Approved Test Device", joined)
        self.assertIn("USB-C port", joined)
        self.assertIn("1007", joined)
        self.assertNotIn("fictional", joined.lower())

    def test_safe_youtube_metadata(self):
        demo = {"code": "1001", "name": "Orbit Dock", "is_demo": True}
        title, description = youtube_metadata(demo)
        self.assertIn("Concept Demo", title)
        self.assertIn("Fictional", description)
        self.assertIn("https://obnote.vercel.app/?code=1001", description)
        self.assertNotIn("Buy now", description)
        real = {"code": "1007", "name": "Approved Device", "is_demo": False}
        title, description = youtube_metadata(real)
        self.assertIn("verify current", description)
        self.assertIn("affiliate disclosure", description)

    def test_srt_timing(self):
        data = storyboard({"code": "1001", "name": "Demo",
                           "features": [], "is_demo": True})
        captions = srt_text(data)
        self.assertIn("00:00:00,000 --> 00:00:02,400", captions)
        self.assertIn("00:00:09,400 --> 00:00:12,400", captions)
        self.assertEqual(srt_time(62.345), "00:01:02,345")


if __name__ == "__main__":
    unittest.main()
