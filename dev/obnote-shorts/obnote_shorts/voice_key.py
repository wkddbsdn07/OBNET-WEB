"""Stable cache identity for an explicit WAV synthesis profile. No I/O."""
import hashlib
import json


def voice_key(*, text: str, language: str, voice: str, provider: str, model_revision: str,
              sample_rate_hz: int, channels: int, speed_percent: int) -> str:
    """Fingerprint exact inputs, not credentials; add a new schema for new controls.

    V1 assumes signed 16-bit little-endian PCM WAV. Provider and revision are
    public identifiers; callers must resolve mutable defaults before keying.
    """
    strings = (text, language, voice, provider, model_revision)
    if not all(isinstance(value, str) and value.strip() for value in strings):
        raise ValueError('Expected nonempty text and explicit synthesis identifiers')
    if not all(type(value) is int and value > 0 for value in (sample_rate_hz, channels, speed_percent)):
        raise ValueError('Expected positive integer audio settings')
    if channels not in (1, 2):
        raise ValueError('Expected mono or stereo PCM')
    fields = ['obnote-voice/v1', *strings, 'wav-pcm-s16le', sample_rate_hz, channels, speed_percent]
    payload = json.dumps(fields, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()
