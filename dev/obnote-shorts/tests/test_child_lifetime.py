"""Linux fixture: parent exits without cleanup; bounded exec child holds the same flock."""
import ctypes
import os
import select
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from obnote_shorts.fixture_slot import (
    FixtureNotClaimed,
    fixture_slot,
    fixture_slot_with_fd,
)
from obnote_shorts.job_store import submit
from obnote_shorts.render_lock import RenderBusy

ROOT = Path(__file__).resolve().parents[1]
CHILD = '''
import os, select, sys
print(os.getpid(), flush=True)
if not select.select([sys.stdin], [], [], 8)[0]: sys.exit(8)
sys.exit(0 if sys.stdin.readline().strip() == 'finish' else 9)
'''
PARENT = '''
import os, subprocess, sys
from pathlib import Path
from obnote_shorts.fixture_slot import fixture_slot_with_fd
with fixture_slot_with_fd(Path(sys.argv[1]), int(sys.argv[2])) as (job, fd):
    subprocess.Popen([sys.executable, '-B', '-c', sys.argv[3]], pass_fds=(fd,))
    os._exit(17)
'''


class ChildLifetimeTest(unittest.TestCase):
    def test_exec_child_excludes_competitor_after_parent_exit(self):
        self.assertTrue(callable(fixture_slot_with_fd))
        scratch = ROOT / '.tmp'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            workspace = Path(folder)
            db = workspace / 'jobs.sqlite'
            a, b = [submit(db, mode='fixture', product_code=c, manifest_sha256='a'*64).id for c in ('A', 'B')]
            # Adopt and reap the orphan in this test, rather than leaving cleanup to PID 1.
            prctl = ctypes.CDLL(None).prctl
            old = ctypes.c_int()
            self.assertEqual(prctl(37, ctypes.byref(old), 0, 0, 0), 0)  # GET_CHILD_SUBREAPER
            self.assertEqual(prctl(36, 1, 0, 0, 0), 0)  # SET_CHILD_SUBREAPER
            try:
                with subprocess.Popen([sys.executable, '-B', '-c', PARENT, folder, str(a), CHILD],
                                      cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as parent:
                    self.assertEqual(parent.wait(timeout=5), 17)
                    self.assertTrue(select.select([parent.stdout], [], [], 5)[0])
                    child = int(parent.stdout.readline())
                    try:
                        with self.assertRaises(RenderBusy), fixture_slot(workspace, b):
                            self.fail('Entered while surviving child was alive')
                    finally:
                        parent.stdin.write('finish\n')
                        parent.stdin.flush()
                        pid, status = os.waitpid(child, 0)
                        self.assertEqual((pid, os.waitstatus_to_exitcode(status)), (child, 0))
                with self.assertRaises(FixtureNotClaimed), fixture_slot(workspace, b):
                    self.fail('Automatic takeover after child exit')
                with closing(sqlite3.connect(db)) as con:
                    self.assertEqual(dict(con.execute('SELECT id,state FROM jobs')), {a: 'running', b: 'queued'})
            finally:
                self.assertEqual(prctl(36, old.value, 0, 0, 0), 0)
