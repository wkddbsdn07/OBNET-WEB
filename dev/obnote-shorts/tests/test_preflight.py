"""Exercise the real offline CLI with ephemeral, non-video fixtures."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PreflightCLI(unittest.TestCase):
    def setUp(self):
        parent = ROOT / '.tmp'
        parent.mkdir(exist_ok=True)
        tmp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)
        self.review = self.folder / 'review.json'
        clip, evidence = b'fixture not video', b'fixture not a grant'
        (self.folder / 'clip').write_bytes(clip)
        (self.folder / 'grant').write_bytes(evidence)
        record = {
            'schema_version': 1, 'product_code': 'TEST-01',
            'source_url': 'https://example.invalid/fixture', 'asset_path': 'clip',
            'asset_sha256': hashlib.sha256(clip).hexdigest(), 'evidence_path': 'grant',
            'evidence_sha256': hashlib.sha256(evidence).hexdigest(), 'rights_holder': 'fixture',
            'permission_basis': 'fixture', 'review_status': 'approved', 'reviewer': 'PRIVATE-MARKER',
            'reviewed_at': '2000-01-01T00:00:00+00:00', 'expires_at': None,
            'allowed_uses': ['preview', 'commercial', 'editing', 'redistribution'],
            'is_test_material': True, 'attribution_required': False, 'attribution_text': '',
        }
        self.review.write_text(json.dumps(record))

    def invoke(self, purpose, code='TEST-01', review=None):
        path = self.review.relative_to(ROOT) if review is None else review
        before = sorted(self.folder.rglob('*'))
        run = subprocess.run([sys.executable, '-B', '-m', 'obnote_shorts.preflight',
                              str(path), code, purpose], cwd=ROOT, capture_output=True,
                             text=True, timeout=10, check=False)
        self.assertEqual(sorted(self.folder.rglob('*')), before)
        self.assertEqual(run.stderr, '')
        self.assertNotIn('PRIVATE-MARKER', run.stdout)
        return run.returncode, json.loads(run.stdout)

    def test_fixture_preview_only(self):
        code, result = self.invoke('preview')
        self.assertEqual(code, 0)
        self.assertEqual(result, {'decision': 'allow', 'purpose': 'preview', 'test_material': True})
        self.assertEqual(self.invoke('distribution'), (1, {'decision': 'deny', 'purpose': 'distribution'}))

    def test_mismatched_product_denied(self):
        self.assertEqual(self.invoke('preview', 'TEST-02'), (1, {'decision': 'deny', 'purpose': 'preview'}))

    def test_malformed_input_denied_without_echo(self):
        self.review.write_text('PRIVATE-MARKER: not JSON')
        self.assertEqual(self.invoke('preview'), (1, {'decision': 'deny', 'purpose': 'preview'}))

    def test_absolute_record_path_denied(self):
        self.assertEqual(self.invoke('preview', review=self.review),
                         (1, {'decision': 'deny', 'purpose': 'preview'}))
