"""Commit an immutable local fixture QA receipt; never render or deliver anything."""
import hashlib
import json
import os
import sqlite3
import stat
from contextlib import closing, contextmanager
from pathlib import Path

from .job_store import Job


@contextmanager
def _regular(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or not info.st_size:
            raise ValueError('Expected a nonempty regular fixture file')
        yield stream


def complete_fixture(workspace: Path, job_id: int) -> Job:
    """Caller owns the workspace lock and has finished writing both files.

    Trust only a local verifier's immutable fixture-ID.qa.json, not user input.
    The verifier is responsible for decoding and quality checks. This transaction
    checks the receipt against the MP4 bytes and ledger, not the media quality.
    """
    if type(job_id) is not int or job_id <= 0:
        raise ValueError('Invalid job ID')
    base = workspace / f'fixture-{job_id}'
    with _regular(base.with_suffix('.qa.json')) as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError('Fixture receipt too large')
    review = json.loads(raw.decode('utf-8'))
    if (not isinstance(review, dict) or review.get('kind') != 'fixture-qa-v1' or review.get('result') != 'pass'
            or type(review.get('job_id')) is not int or review['job_id'] != job_id):
        raise ValueError('Not a passing receipt for this fixture')
    with _regular(base.with_suffix('.mp4')) as stream:
        output_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    if output_hash != review.get('output_sha256'):
        raise ValueError('Fixture does not match verified output')
    receipt = output_hash, hashlib.sha256(raw).hexdigest()
    uri = (workspace / 'jobs.sqlite').resolve().as_uri() + '?mode=rw'
    with closing(sqlite3.connect(uri, uri=True, timeout=5)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT state,manifest_sha256 FROM jobs WHERE id=? AND mode=\'fixture\'', (job_id,)).fetchone()
        if not row or row[0] not in ('running', 'completed') or row[1] != review.get('manifest_sha256'):
            raise ValueError('Fixture state or manifest mismatch')
        db.execute('CREATE TABLE IF NOT EXISTS fixture_completions (job_id INTEGER PRIMARY KEY REFERENCES jobs(id), '
                   'output_sha256 TEXT NOT NULL, receipt_sha256 TEXT NOT NULL)')
        if row[0] == 'completed':
            stored = db.execute('SELECT output_sha256,receipt_sha256 FROM fixture_completions WHERE job_id=?',
                                (job_id,)).fetchone()
            if stored != receipt:
                raise ValueError('Completed fixture lacks the identical receipt')
        else:
            db.execute('INSERT INTO fixture_completions(job_id,output_sha256,receipt_sha256) VALUES(?,?,?)',
                       (job_id, *receipt))
            db.execute("UPDATE jobs SET state='completed' WHERE id=? AND state='running'", (job_id,))
    return Job(job_id, 'completed')
