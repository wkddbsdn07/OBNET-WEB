"""Read-only structural validation of the cache's canonical RIFF PCM16 WAV subset."""
import os
import stat
import struct
from pathlib import Path

_HEADER = struct.Struct('<4sI4s4sIHHIIHH4sI')


def inspect_cached_wav(path: Path, *, sample_rate_hz: int, channels: int, scene_ms: int) -> int:
    """Return the sample-frame count, or reject without trimming or synthesis.

    Intended for trusted stable cache directories. Only canonical 16-byte fmt
    followed by data is supported; metadata/extensible headers are not accepted.
    This checks structure and timing, not words, sample integrity or voice quality.
    """
    if not all(type(x) is int and x > 0 for x in (sample_rate_hz, channels, scene_ms)) or channels not in (1, 2):
        raise ValueError('Invalid requested profile or scene duration')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('Expected regular cached WAV')
        raw = stream.read(_HEADER.size)
        if len(raw) != _HEADER.size:
            raise ValueError('Incomplete WAV header')
        riff, size, wave, fmt, fmt_len, codec, ch, rate, byte_rate, align, bits, data, length = _HEADER.unpack(raw)
        if (riff, wave, fmt, fmt_len, data) != (b'RIFF', b'WAVE', b'fmt ', 16, b'data'):
            raise ValueError('Unsupported WAV structure')
        if (codec, ch, rate, bits, align, byte_rate) != (1, channels, sample_rate_hz, 16,
                                                         2 * channels, 2 * channels * sample_rate_hz):
            raise ValueError('Cached WAV profile mismatch')
        if size + 8 != info.st_size or length + _HEADER.size != info.st_size or not length or length % align:
            raise ValueError('Incomplete or inconsistent PCM payload')
        frames = length // align
        if frames * 1000 > scene_ms * rate:
            raise ValueError('Cached WAV exceeds scene duration')
        return frames
