"""Advisory Linux lock for cooperating processes using one stable render directory."""
import fcntl
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class RenderBusy(RuntimeError):
    """Another holder owns the render workspace."""


@contextmanager
def render_lock_fd(workspace: Path) -> Iterator[int]:
    """Lock the dedicated directory inode, not a per-job file or a SQLite row.

    All workers must use the same existing, trusted local directory; do not
    replace it while workers are active. The lock is not a recovery decision.
    """
    fd = os.open(workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RenderBusy('Render workspace is occupied') from exc
        # Borrowed descriptor: never close or explicitly unlock it in the caller.
        # A trusted direct child may inherit it via Popen(pass_fds=(fd,)).
        yield fd
    finally:
        os.close(fd)


@contextmanager
def render_lock(workspace: Path) -> Iterator[None]:
    with render_lock_fd(workspace):
        yield
