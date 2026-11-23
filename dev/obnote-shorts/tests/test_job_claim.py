"""Ledger-only claim tests; no workers, encoders, or production DBs."""
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Barrier

from obnote_shorts.job_claim import claim_fixture
from obnote_shorts.job_store import Job, submit


class ClaimTest(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[1] / '.tmp'
        parent.mkdir(exist_ok=True)
        folder = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(folder.cleanup)
        self.db = Path(folder.name) / 'jobs.sqlite'

    def add(self, code, mode='fixture'):
        return submit(self.db, product_code=code, mode=mode, manifest_sha256='a'*64).id

    def test_competing_claims_and_persisted_exclusion(self):
        ids = [self.add('A'), self.add('B')]
        gate = Barrier(2)

        def race(key):
            gate.wait(timeout=5)
            return claim_fixture(self.db, key)

        with ThreadPoolExecutor(max_workers=2) as pool:
            replies = list(pool.map(race, ids))
        self.assertEqual(replies.count(None), 1)
        winner = next(r for r in replies if r is not None)
        self.assertEqual(winner, Job(ids[replies.index(winner)], 'running'))
        loser = ids[replies.index(None)]
        self.assertIsNone(claim_fixture(self.db, loser))
        with closing(sqlite3.connect(self.db)) as db, db:
            self.assertEqual(dict(db.execute('SELECT id,state FROM jobs')),
                             {winner.id: 'running', loser: 'queued'})
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE jobs SET state='running' WHERE id=?", (loser,))
            db.execute("UPDATE jobs SET state='completed' WHERE id=?", (winner.id,))
        self.assertEqual(claim_fixture(self.db, loser), Job(loser, 'running'))

    def test_terminal_distribution_and_missing_not_claimed(self):
        targets = {self.add(state): state for state in ('cancelled', 'failed', 'completed')}
        with closing(sqlite3.connect(self.db)) as db, db:
            db.executemany('UPDATE jobs SET state=? WHERE id=?', [(s, i) for i, s in targets.items()])
        targets[self.add('DIST', 'distribution')] = 'queued'
        for key in (*targets, 999):
            self.assertIsNone(claim_fixture(self.db, key))
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(dict(db.execute('SELECT id,state FROM jobs')), targets)
