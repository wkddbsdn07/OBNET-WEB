"""Submission only: use isolated on-disk databases, no real jobs or workers."""
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Barrier

from obnote_shorts.job_store import submit


class JobStoreTest(unittest.TestCase):
    def setUp(self):
        tmp = Path(__file__).resolve().parents[1] / '.tmp'
        tmp.mkdir(exist_ok=True)
        folder = tempfile.TemporaryDirectory(dir=tmp)
        self.addCleanup(folder.cleanup)
        self.db = Path(folder.name) / 'jobs.sqlite'
        self.args = {'mode': 'fixture', 'product_code': 'TEST-01', 'manifest_sha256': 'a' * 64}

    def enqueue(self, **changes):
        return submit(self.db, **(self.args | changes))

    def test_reopen_and_resubmit(self):
        first = self.enqueue()
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute('SELECT id,state FROM jobs').fetchall(), [(first.id, 'queued')])
        self.assertEqual(first, self.enqueue())

    def test_changed_inputs_are_distinct(self):
        ids = {self.enqueue().id, self.enqueue(mode='distribution').id,
               self.enqueue(product_code='test-01').id, self.enqueue(manifest_sha256='b' * 64).id}
        self.assertEqual(len(ids), 4)

    def test_duplicate_never_requeues_cancelled_job(self):
        first = self.enqueue()
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("UPDATE jobs SET state='cancelled' WHERE id=?", (first.id,))
        retried = self.enqueue()
        self.assertEqual((retried.id, retried.state), (first.id, 'cancelled'))

    def test_concurrent_submissions_create_one_row(self):
        barrier = Barrier(4)

        def race(_):
            barrier.wait(timeout=5)
            return self.enqueue()

        with ThreadPoolExecutor(max_workers=4) as pool:
            replies = list(pool.map(race, range(4)))
        self.assertEqual(len(set(replies)), 1)
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(con.execute('SELECT count(*) FROM jobs').fetchone(), (1,))

    def test_invalid_input_creates_no_database(self):
        for change in ({'mode': 'preview'}, {'product_code': ' TEST-01'}, {'manifest_sha256': 'A' * 64}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.enqueue(**change)
        self.assertFalse(self.db.exists())
