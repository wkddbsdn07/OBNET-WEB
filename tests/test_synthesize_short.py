import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from synthesize_short import create_voice_segments, mux_voice


class SynthesisTest(unittest.TestCase):
    def test_voice_segments_fit_timeline(self):
        scenes = []
        start = 0
        for words in ("Meet the demo.", "Concept technology.", "Not a real product.",
                      "Search by code.", "Find it on OBNOTE."):
            scenes.append({"start_seconds": start, "end_seconds": start + 2.5,
                           "narration": words})
            start += 2.5
        plan = {"segments": scenes}

        def fake_synth(command, **kwargs):
            output = Path(command[command.index("-w") + 1])
            with wave.open(str(output), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(22050)
                wav.writeframes(bytes(22050 * 2))

        with tempfile.TemporaryDirectory() as tmp:
            with patch("synthesize_short.subprocess.run", side_effect=fake_synth) as run:
                paths, durations = create_voice_segments(plan, Path(tmp))
            self.assertEqual(run.call_count, 5)
            self.assertTrue(all(path.is_file() for path in paths))
            self.assertEqual(durations, [2.5] * 5)

    def test_mux_voice_builds_padded_scene_concat(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "silent.mp4"
            video.write_bytes(b"placeholder")
            tracks = [root / f"voice-{i}.wav" for i in range(5)]
            for track in tracks:
                track.write_bytes(b"placeholder")
            output = root / "final.mp4"

            def fake_mux(command, **kwargs):
                output.write_bytes(b"synthetic-video")
            with patch("synthesize_short.subprocess.run", side_effect=fake_mux) as run:
                mux_voice(video, tracks, [2.4, 2.2, 2.8, 2.0, 3.0],
                          output, ffmpeg="/usr/bin/ffmpeg")
            argv = run.call_args.args[0]
            self.assertIn("concat=n=5:v=0:a=1", " ".join(argv))
            self.assertIn("-c:a", argv)
            self.assertTrue(output.is_file())

    def test_mismatched_track_count_rejected(self):
        with self.assertRaises(ValueError):
            mux_voice(Path("in.mp4"), [], [2.4], Path("out.mp4"), ffmpeg="ffmpeg")


if __name__ == "__main__":
    unittest.main()
