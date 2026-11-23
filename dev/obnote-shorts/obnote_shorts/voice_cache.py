"""Offline append-only cache for trusted audio bytes. No provider calls or eviction."""
import fcntl
import hashlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile


class CacheFull(ValueError):
    """Refused a write rather than exceed the configured payload cap."""


@dataclass(frozen=True)
class VoiceCache:
    """All writers share one stable, private directory and the same byte limit.

    Keys are lowercase SHA-256 request fingerprints supplied by the caller.
    Count logical file lengths, including abandoned staging files, not disk blocks.
    """

    folder: Path
    max_bytes: int

    def __post_init__(self):
        if type(self.max_bytes) is not int or self.max_bytes < 0:
            raise ValueError('Expected a nonnegative byte cap')

    def _path(self, key):
        if not isinstance(key, str) or not re.fullmatch(r'[0-9a-f]{64}', key):
            raise ValueError('Expected a lowercase SHA-256 request fingerprint')
        return self.folder / (key + '.wav')

    def lookup(self, key):
        path = self._path(key)
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(mode):
            raise ValueError('Unexpected cache entry type')
        return path

    def store(self, key, audio):
        path = self._path(key)
        if not isinstance(audio, bytes) or not audio:
            raise ValueError('Expected nonempty audio bytes')
        fd = os.open(self.folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            if self.lookup(key) is not None:
                with path.open('rb') as stream:
                    if hashlib.file_digest(stream, 'sha256').digest() != hashlib.sha256(audio).digest():
                        raise ValueError('Conflicting audio for existing request')
                return path
            used = 0
            for entry in self.folder.iterdir():
                info = entry.lstat()
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError('Cache directory must contain only regular files')
                used += info.st_size
            if len(audio) > self.max_bytes - used:
                raise CacheFull('Insufficient cache capacity')
            with NamedTemporaryFile(dir=self.folder, prefix='.stage-', delete=False) as stream:
                temp = Path(stream.name)
                try:
                    stream.write(audio)
                    stream.flush()
                    os.fsync(stream.fileno())
                    os.replace(temp, path)
                    os.fsync(fd)
                finally:
                    temp.unlink(missing_ok=True)
            return path
        finally:
            os.close(fd)
