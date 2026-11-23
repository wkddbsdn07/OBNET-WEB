"""Real subprocess tests; fixture workspace and ledger only."""
import select
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from obnote_shorts.job_claim import claim_fixture
from obnote_shorts.job_store import submit
from obnote_shorts.render_lock import RenderBusy, render_lock

ROOT = Path(__file__).resolve().parents[1]
HOLDER = '''
import os, sys
from pathlib import Path
from obnote_shorts.render_lock import render_lock
with render_lock(Path(sys.argv[1])):
    print('locked', flush=True)
    if sys.stdin.readline().strip() == 'abrupt':
        os._exit(17)
'''


class RenderLockTest(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / '.tmp'
        scratch.mkdir(exist_ok=True)
        tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)

    def exercise_exit(self, how, expected):
        with subprocess.Popen([sys.executable, '-B', '-c', HOLDER, str(self.folder)], cwd=ROOT,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as proc:
            try:
                self.assertTrue(select.select([proc.stdout], [], [], 5)[0], 'holder did not signal readiness')
                self.assertEqual(proc.stdout.readline(), 'locked\n')
                with self.assertRaises(RenderBusy), render_lock(self.folder):
                    self.fail('second process entered occupied workspace')
                proc.stdin.write(how + '\n')
                proc.stdin.flush()
                self.assertEqual(proc.wait(timeout=5), expected)
            finally:
                if proc.poll() is None:
                    proc.kill()
        with render_lock(self.folder):
            pass

    def test_normal_exit_releases(self):
        self.exercise_exit('normal', 0)

    def test_abrupt_exit_releases_lock_without_resetting_ledger(self):
        db = self.folder / 'jobs.sqlite'
        args = {'manifest_sha256': 'a'*64, 'mode': 'fixture'}
        active = submit(db, product_code='ACTIVE', **args).id
        cancelled = submit(db, product_code='CANCELLED', **args).id
        self.assertIsNotNone(claim_fixture(db, active))
        with closing(sqlite3.connect(db)) as con, con:
            con.execute("UPDATE jobs SET state='cancelled' WHERE id=?", (cancelled,))
        self.exercise_exit('abrupt', 17)
        with closing(sqlite3.connect(db)) as con:
            self.assertEqual(dict(con.execute('SELECT id,state FROM jobs')), {active: 'running', cancelled: 'cancelled'})
