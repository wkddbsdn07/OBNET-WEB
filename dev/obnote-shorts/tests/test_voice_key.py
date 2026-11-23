"""Pure request identity and cache reuse; no provider or synthesized speech."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from obnote_shorts.voice_cache import VoiceCache
from obnote_shorts.voice_key import voice_key

REQUEST = {
    'text': 'Demo 한글.', 'language': 'en-US', 'voice': 'fixture-A',
    'provider': 'fixture', 'model_revision': 'demo@1', 'sample_rate_hz': 24000,
    'channels': 1, 'speed_percent': 100,
}


class VoiceKeyTest(unittest.TestCase):
    def test_versioned_wire_format_and_argument_order(self):
        vector = ('["obnote-voice/v1","Demo 한글.","en-US","fixture-A","fixture",'
                  '"demo@1","wav-pcm-s16le",24000,1,100]').encode()
        expected = hashlib.sha256(vector).hexdigest()
        self.assertEqual(voice_key(**REQUEST), expected)
        self.assertEqual(voice_key(**dict(reversed(REQUEST.items()))), expected)

    def test_settings_and_exact_text_change_identity(self):
        changes = {'text': 'Demo 한글. ', 'language': 'ko-KR', 'voice': 'fixture-B',
                   'provider': 'other', 'model_revision': 'demo@2', 'sample_rate_hz': 48000,
                   'channels': 2, 'speed_percent': 99}
        self.assertEqual(len({voice_key(**REQUEST)} | {
            voice_key(**(REQUEST | {field: value})) for field, value in changes.items()
        }), 1 + len(changes))

    def test_invalid_or_ambiguous_configuration_is_rejected(self):
        for field, value in [('text', ' '), ('provider', ''), ('channels', True),
                             ('channels', 3), ('sample_rate_hz', 0), ('speed_percent', 100.0)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                voice_key(**(REQUEST | {field: value}))

    def test_cache_hit_and_different_voice_miss(self):
        scratch = Path(__file__).resolve().parents[1] / '.tmp'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            cache = VoiceCache(Path(tmp), 16)
            first = cache.store(voice_key(**REQUEST), b'fixture bytes')
            self.assertEqual(cache.lookup(voice_key(**REQUEST)), first)
            self.assertIsNone(cache.lookup(voice_key(**(REQUEST | {'voice': 'fixture-B'}))))
