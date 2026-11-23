"""Pre-mux checks on locally generated silent WAVs; no speech service."""
import io
import tempfile
import unittest
import wave
from pathlib import Path

from obnote_shorts.cached_wav import inspect_cached_wav


def wav_bytes(frames=80, rate=8000, channels=1, width=2):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as out:
        out.setparams((channels, width, rate, 0, 'NONE', 'not compressed'))
        out.writeframes(bytes(frames * channels * width))
    return buf.getvalue()


class CachedWavTest(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / '.tmp'
        scratch.mkdir(exist_ok=True)
        tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / 'fixture.wav'

    def check_audio(self, data):
        self.path.write_bytes(data)
        try:
            return inspect_cached_wav(self.path, sample_rate_hz=8000, channels=1, scene_ms=10)
        finally:
            self.assertEqual(self.path.read_bytes(), data)

    def test_exact_fit_or_shorter_silence(self):
        for frames in (79, 80):
            with self.subTest(frames=frames):
                self.assertEqual(self.check_audio(wav_bytes(frames)), frames)

    def test_one_frame_over_not_trimmed(self):
        with self.assertRaisesRegex(ValueError, 'duration'):
            self.check_audio(wav_bytes(81))

    def test_invalid_profile_rejected(self):
        for data in (wav_bytes(rate=16000), wav_bytes(channels=2), wav_bytes(width=1)):
            with self.subTest(header=data[:44]), self.assertRaisesRegex(ValueError, 'profile'):
                self.check_audio(data)

    def test_empty_and_structurally_damaged_rejected(self):
        for data in (b'garbage', wav_bytes()[:-1], wav_bytes(0), wav_bytes()+b'extra'):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                self.check_audio(data)
