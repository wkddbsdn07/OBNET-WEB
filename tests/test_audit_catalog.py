import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from audit_catalog import find_issues


class CatalogAuditTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 15, 8, tzinfo=timezone.utc)
        self.good = {
            "code": "1007", "is_demo": False, "price": 25.5,
            "price_checked_at": self.now.isoformat(),
            "stock_status": "in_stock",
            "stock_checked_at": self.now.isoformat(),
        }

    def test_current_reporting_is_ok(self):
        count, issues = find_issues([self.good], self.now)
        self.assertEqual(count, 1)
        self.assertEqual(issues, [])

    def test_demo_excluded(self):
        count, issues = find_issues([{"code": "1001", "is_demo": True}], self.now)
        self.assertEqual(count, 0)
        self.assertEqual(issues, [])

    def test_unknown_stock_flagged(self):
        p = {**self.good, "stock_status": "unknown", "stock_checked_at": None}
        count, issues = find_issues([p], self.now)
        self.assertEqual(count, 1)
        self.assertEqual(len(issues), 1)
        self.assertIn("Stock", issues[0][1])

    def test_stale_price_and_stock_flagged(self):
        before = (self.now - timedelta(days=8)).isoformat()
        p = {**self.good, "price_checked_at": before, "stock_checked_at": before}
        count, issues = find_issues([p], self.now)
        self.assertEqual(count, 1)
        self.assertEqual(len(issues), 2)

    def test_missing_price_not_marked_stale(self):
        p = {**self.good, "price": None, "price_checked_at": None}
        count, issues = find_issues([p], self.now)
        self.assertEqual(count, 1)
        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
