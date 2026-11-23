"""Offline fixtures only: passing these tests establishes no actual media rights."""
import copy
import hashlib
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from obnote_shorts.media_permissions import PermissionDenied, validate_media

NOW = datetime(2026, 11, 17, tzinfo=UTC)


class MediaPermissionTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[1] / '.tmp'
        parent.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'clip.bin').write_bytes(b'NOT VIDEO: unit test asset')
        (self.root / 'grant.txt').write_text('NOT A LICENSE: unit test evidence')
        self.record = {
            'schema_version': 1,
            'product_code': 'TEST-01',
            'source_url': 'https://example.invalid/product/TEST-01/video',
            'asset_path': 'clip.bin',
            'asset_sha256': self.digest('clip.bin'),
            'evidence_path': 'grant.txt',
            'evidence_sha256': self.digest('grant.txt'),
            'rights_holder': 'FICTIONAL test rights holder',
            'permission_basis': 'FICTIONAL written grant for test only',
            'review_status': 'approved',
            'reviewer': 'unit-test-reviewer',
            'reviewed_at': '2026-11-16T00:00:00+00:00',
            'expires_at': None,
            'allowed_uses': ['preview', 'commercial', 'editing', 'redistribution'],
            'is_test_material': True,
            'attribution_required': True,
            'attribution_text': 'UNIT TEST FIXTURE ONLY',
        }

    def digest(self, name):
        return hashlib.sha256((self.root / name).read_bytes()).hexdigest()

    def validate(self, record=None, purpose='preview', product_code='TEST-01'):
        return validate_media(self.record if record is None else record,
                              workspace=self.root, product_code=product_code,
                              purpose=purpose, now=NOW)

    def test_preview_keeps_fixture_label_and_attribution(self):
        result = self.validate()
        self.assertTrue(result.is_test_material)
        self.assertEqual(result.asset_sha256, self.record['asset_sha256'])
        self.assertEqual(result.attribution_text, 'UNIT TEST FIXTURE ONLY')

    def test_fixture_cannot_be_distributed(self):
        with self.assertRaises(PermissionDenied):
            self.validate(purpose='distribution')

    def test_distribution_record_contract_only_not_real_authorization(self):
        self.record['is_test_material'] = False  # Schema exercise, not real rights.
        self.assertEqual(self.validate(purpose='distribution').purpose, 'distribution')

    def test_all_required_fields_fail_closed(self):
        for field in self.record:
            with self.subTest(field=field):
                record = copy.deepcopy(self.record)
                del record[field]
                with self.assertRaises(PermissionDenied):
                    self.validate(record)

    def test_unapproved_or_blank_review_rejected(self):
        for field, value in [('review_status', 'pending'), ('review_status', 'revoked'),
                             ('reviewer', ' '), ('rights_holder', ''),
                             ('permission_basis', ''), ('product_code', 'OTHER'),
                             ('schema_version', True), ('is_test_material', 'false')]:
            with self.subTest(field=field, value=value):
                record = dict(self.record, **{field: value})
                with self.assertRaises(PermissionDenied):
                    self.validate(record)

    def test_each_distribution_use_required(self):
        self.record['is_test_material'] = False
        for usage in ('commercial', 'editing', 'redistribution'):
            with self.subTest(usage=usage):
                record = dict(self.record, allowed_uses=[u for u in self.record['allowed_uses'] if u != usage])
                with self.assertRaises(PermissionDenied):
                    self.validate(record, purpose='distribution')

    def test_preview_permission_required(self):
        self.record['allowed_uses'] = ['commercial']
        with self.assertRaises(PermissionDenied):
            self.validate()

    def test_asset_and_evidence_tampering_rejected(self):
        for name in ('clip.bin', 'grant.txt'):
            with self.subTest(name=name):
                path = self.root / name
                before = path.read_bytes()
                path.write_bytes(b'tampered')
                with self.assertRaises(PermissionDenied):
                    self.validate()
                path.write_bytes(before)

    def test_missing_file_rejected(self):
        (self.root / 'grant.txt').unlink()
        with self.assertRaises(PermissionDenied):
            self.validate()

    def test_paths_must_stay_inside_workspace_without_symlinks(self):
        (self.root / 'alias').symlink_to(self.root / 'clip.bin')
        for value in ('../outside', str(self.root / 'clip.bin'), 'alias', '.', ''):
            with self.subTest(value=value), self.assertRaises(PermissionDenied):
                self.validate(dict(self.record, asset_path=value))

    def test_hashes_are_not_silently_normalized(self):
        for value in ('a' * 63, self.record['asset_sha256'].upper(), ' ' + self.record['asset_sha256']):
            with self.subTest(value=value), self.assertRaises(PermissionDenied):
                self.validate(dict(self.record, asset_sha256=value))

    def test_invalid_or_credentialed_provenance_rejected(self):
        for url in ('file:///etc/passwd', 'http://example.invalid/video', 'https://',
                    'https://user:password@example.invalid/video'):
            with self.subTest(url=url), self.assertRaises(PermissionDenied):
                self.validate(dict(self.record, source_url=url))

    def test_review_and_expiry_timestamps(self):
        for field, value in [('reviewed_at', 'not-a-date'),
                             ('reviewed_at', '2026-11-18T00:00:00+00:00'),
                             ('reviewed_at', '2026-11-16T00:00:00'),
                             ('expires_at', NOW.isoformat()),
                             ('expires_at', '2026-11-15T00:00:00+00:00')]:
            with self.subTest(field=field, value=value), self.assertRaises(PermissionDenied):
                self.validate(dict(self.record, **{field: value}))

    def test_required_attribution_cannot_be_empty(self):
        with self.assertRaises(PermissionDenied):
            self.validate(dict(self.record, attribution_text=' '))

    def test_unknown_purpose_and_malformed_records_fail_closed(self):
        with self.assertRaises(PermissionDenied):
            self.validate(purpose='publish')
        for record in ([], 'approved', {'schema_version': 1}):
            with self.subTest(record=record), self.assertRaises(PermissionDenied):
                self.validate(record)


if __name__ == '__main__':
    unittest.main()
