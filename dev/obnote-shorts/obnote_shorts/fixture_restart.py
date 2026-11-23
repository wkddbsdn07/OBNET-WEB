"""Read-only restart check of a trusted, quiescent, single-input fixture workspace."""
import hashlib
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from .fixture_completion import _regular

ROOT = Path(__file__).resolve().parents[1]


def inspect(workspace: Path, job_id: int) -> str:
    """Return receipt_matches or a reason for operator review; never modify jobs."""
    if type(job_id) is not int or job_id <= 0:
        return 'invalid_job_id'
    db_file = workspace / 'jobs.sqlite'
    if db_file.is_symlink() or not db_file.is_file():
        return 'ledger_unavailable'
    try:
        with closing(sqlite3.connect(db_file.as_uri() + '?mode=ro', uri=True, timeout=2)) as db:
            row = db.execute('SELECT j.mode,j.state,j.manifest_sha256,c.output_sha256,c.receipt_sha256 '
                             'FROM jobs j LEFT JOIN fixture_completions c ON c.job_id=j.id WHERE j.id=?',
                             (job_id,)).fetchone()
    except sqlite3.Error:
        return 'ledger_unavailable'
    if not row or row[:2] != ('fixture', 'completed') or not all(row[2:]):
        return 'no_completed_fixture_receipt'
    # The completion transaction already checked the receipt semantics. Match its
    # exact bytes rather than accepting a new, merely similar passing receipt.
    names = ('input.json', f'fixture-{job_id}.mp4', f'fixture-{job_id}.qa.json')
    for name, expected in zip(names, row[2:], strict=True):
        try:
            with _regular(workspace / name) as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        except FileNotFoundError:
            return 'missing:' + name
        except (OSError, ValueError):
            return 'unreadable:' + name
        if actual != expected:
            return 'mismatch:' + name
    return 'receipt_matches'


def main(args):
    if len(args) != 2 or not args[1].isascii() or not args[1].isdecimal() or len(args[1]) > 18:
        return 2
    relative = Path(args[0])
    if relative.is_absolute() or '..' in relative.parts:
        return 2
    workspace = (ROOT / relative).resolve()
    if not workspace.is_relative_to(ROOT):
        return 2
    key = int(args[1])
    detail = inspect(workspace, key)
    ok = detail == 'receipt_matches'
    print(json.dumps({'job_id': key, 'decision': 'verified_complete' if ok else 'review_required', 'detail': detail}))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
