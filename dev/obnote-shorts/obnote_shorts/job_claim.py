"""Reserve the one running slot in an existing ledger; this never starts a process."""
import sqlite3
from contextlib import closing
from pathlib import Path

from .job_store import Job


def claim_fixture(database: Path, job_id: int) -> Job | None:
    """Claim exactly the named queued fixture, or leave its state unchanged.

    The slot covers both modes in the same database. Never reclaim running rows
    on timeout/reopen. Distribution requires a separate verified execution path.
    """
    if type(job_id) is not int or job_id < 1:
        raise ValueError('Expected a positive integer job ID')
    uri = database.resolve().as_uri() + '?mode=rw'
    with closing(sqlite3.connect(uri, uri=True, timeout=5)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS jobs_one_running ON jobs(state) WHERE state='running'")
        changed = db.execute("UPDATE jobs SET state='running' WHERE id=? AND state='queued' AND mode='fixture' "
                             "AND NOT EXISTS (SELECT 1 FROM jobs WHERE state='running')", (job_id,))
        return Job(job_id, 'running') if changed.rowcount == 1 else None
