"""Cache admission with real, locally constructed silent WAV bytes, never TTS."""
import io
import tempfile
import unittest
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from obnote_shorts.voice_cache import CacheFull, VoiceCache


class VoiceCacheTest(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / '.tmp'
        scratch.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
            wav.writeframes(bytes(160))
        self.audio = buffer.getvalue()
        self.cache = VoiceCache(self.folder, len(self.audio))

    def test_exact_cap_replay_and_read_after_reopen(self):
        key = 'a' * 64
        self.assertIsNone(self.cache.lookup(key))
        first = self.cache.store(key, self.audio)
        self.assertEqual(self.cache.store(key, self.audio), first)
        self.assertEqual(VoiceCache(self.folder, len(self.audio)).lookup(key).read_bytes(), self.audio)
        with self.assertRaises(ValueError):
            self.cache.store(key, b'other audio')
        self.assertEqual(first.read_bytes(), self.audio)

    def test_rejection_keeps_existing_file_and_counts_unfinished_bytes(self):
        partial = self.folder / '.partial'
        partial.write_bytes(b'x')
        with self.assertRaises(CacheFull):
            self.cache.store('a'*64, self.audio)
        self.assertEqual(list(self.folder.iterdir()), [partial])
        partial.unlink()
        first = self.cache.store('a'*64, self.audio)
        with self.assertRaises(CacheFull):
            self.cache.store('b'*64, self.audio)
        self.assertEqual(list(self.folder.iterdir()), [first])
        self.assertEqual(first.read_bytes(), self.audio)

    def test_competing_writers_cannot_exceed_cap(self):
        gate = Barrier(2)

        def store(key):
            gate.wait(timeout=5)
            try:
                self.cache.store(key, self.audio)
            except CacheFull:
                return False
            return True

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(store, ('a'*64, 'b'*64))), [False, True])
        self.assertEqual(sum(p.stat().st_size for p in self.folder.iterdir()), len(self.audio))
