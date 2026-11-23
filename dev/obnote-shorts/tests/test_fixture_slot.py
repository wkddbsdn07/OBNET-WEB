"""Integration checks for lock-before-claim, without an encoder or provider."""
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from obnote_shorts.fixture_slot import FixtureNotClaimed, fixture_slot
from obnote_shorts.job_store import submit
from obnote_shorts.render_lock import RenderBusy, render_lock


class FixtureSlotTest(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / '.tmp'
        scratch.mkdir(exist_ok=True)
        tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(tmp.cleanup)
        self.workspace = Path(tmp.name)
        self.db = self.workspace / 'jobs.sqlite'

    def add(self, code, mode='fixture'):
        return submit(self.db, product_code=code, manifest_sha256='a' * 64, mode=mode).id

    def states(self):
        with closing(sqlite3.connect(self.db)) as db:
            return dict(db.execute('SELECT id,state FROM jobs'))

    def test_occupied_lock_leaves_target_queued(self):
        target = self.add('WAIT')
        with render_lock(self.workspace), self.assertRaises(RenderBusy), fixture_slot(self.workspace, target):
            self.fail('Entered occupied slot')
        self.assertEqual(self.states(), {target: 'queued'})

    def test_body_holds_lock_and_stale_claim_survives_exception(self):
        target, other = self.add('FIRST'), self.add('SECOND')
        with self.assertRaisesRegex(RuntimeError, 'fixture interruption'), fixture_slot(self.workspace, target) as job:
            self.assertEqual((job.id, job.state), (target, 'running'))
            with self.assertRaises(RenderBusy), render_lock(self.workspace):
                self.fail('Released the lock too early')
            raise RuntimeError('fixture interruption')
        for key in (target, other):
            with self.assertRaises(FixtureNotClaimed), fixture_slot(self.workspace, key):
                self.fail('Took over a stale claim')
        self.assertEqual(self.states(), {target: 'running', other: 'queued'})

    def test_ineligible_jobs_do_not_enter_or_keep_lock(self):
        cancelled, distribution = self.add('CANCEL'), self.add('DIST', 'distribution')
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("UPDATE jobs SET state='cancelled' WHERE id=?", (cancelled,))
        for key in (cancelled, distribution):
            with self.assertRaises(FixtureNotClaimed), fixture_slot(self.workspace, key):
                self.fail('Entered an ineligible slot')
        with render_lock(self.workspace):
            self.assertEqual(self.states(), {cancelled: 'cancelled', distribution: 'queued'})
