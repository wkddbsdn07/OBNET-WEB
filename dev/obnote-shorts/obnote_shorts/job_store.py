"""SQLite submission ledger. Enqueuing a request neither approves nor executes it."""
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

_SCHEMA = """CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    mode TEXT NOT NULL CHECK(mode IN ('fixture','distribution')),
    product_code TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'queued' CHECK(state IN ('queued','running','completed','failed','cancelled')),
    UNIQUE(mode, product_code, manifest_sha256)
)"""


@dataclass(frozen=True)
class Job:
    id: int
    state: str


def submit(database: Path, *, mode: str, product_code: str, manifest_sha256: str) -> Job:
    """Persist intent in a trusted application-owned DB. No state change on duplicate.

    Caller supplies the hash of an immutable input manifest covering all inputs
    (including source versions, language/voice and render configuration). This
    ledger stores its reference, not the manifest, and does not verify its rights.
    """
    if mode not in ('fixture', 'distribution'):
        raise ValueError('Expected fixture or distribution mode')
    if not isinstance(product_code, str) or not re.fullmatch(r'[A-Za-z0-9-]{1,24}', product_code):
        raise ValueError('Invalid product code')
    if not isinstance(manifest_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', manifest_sha256):
        raise ValueError('Expected a lowercase SHA-256 digest')
    key = mode, product_code, manifest_sha256
    with closing(sqlite3.connect(database, timeout=5)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        db.execute(_SCHEMA)
        db.execute('INSERT INTO jobs(mode,product_code,manifest_sha256) VALUES(?,?,?) '
                   'ON CONFLICT(mode,product_code,manifest_sha256) DO NOTHING', key)
        row = db.execute('SELECT id,state FROM jobs WHERE mode=? AND product_code=? AND manifest_sha256=?',
                         key).fetchone()
        return Job(*row)
