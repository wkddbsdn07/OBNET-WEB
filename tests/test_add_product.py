import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from add_product import add_product, next_code


class ProductCodesTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.catalog = Path(self.dir.name) / "products.json"
        self.catalog.write_text(
            json.dumps([{"code": "1001"}, {"code": "1002"}, {"code": "1003"}]),
            encoding="utf-8",
        )
        self.item = {
            "name": "Test Dock",
            "category": "DESK TECH",
            "description": "A test-only item.",
            "tagline": "Test",
            "features": "USB-C|Compact",
            "image_url": "",
            "price": "29.99",
            "currency": "USD",
            "purchase_url": "https://example.com/dock",
            "is_demo": "true",
        }

    def tearDown(self):
        self.dir.cleanup()

    def test_sequential_unique_codes(self):
        self.assertEqual(add_product(self.item, self.catalog), "1004")
        self.assertEqual(add_product(self.item, self.catalog), "1005")
        data = json.loads(self.catalog.read_text(encoding="utf-8"))
        self.assertEqual([x["code"] for x in data][-2:], ["1004", "1005"])
        self.assertEqual(len({p["code"] for p in data}), len(data))

    def test_demo_hides_price_and_link(self):
        add_product(self.item, self.catalog)
        saved = json.loads(self.catalog.read_text(encoding="utf-8"))[-1]
        self.assertIsNone(saved["price"])
        self.assertIsNone(saved["purchase_url"])
        self.assertTrue(saved["is_demo"])

    def test_real_product_can_store_price_and_seller_url(self):
        item = {**self.item, "is_demo": "false"}
        add_product(item, self.catalog)
        saved = json.loads(self.catalog.read_text(encoding="utf-8"))[-1]
        self.assertEqual(saved["price"], 29.99)
        self.assertEqual(saved["purchase_url"], "https://example.com/dock")

    def test_existing_duplicate_refuses_changes(self):
        self.catalog.write_text(
            json.dumps([{"code": "1001"}, {"code": "1001"}]), encoding="utf-8"
        )
        before = self.catalog.read_text(encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            add_product(self.item, self.catalog)
        self.assertEqual(self.catalog.read_text(encoding="utf-8"), before)

    def test_invalid_image_url_refuses_changes(self):
        item = {**self.item, "image_url": "javascript:alert(1)"}
        before = self.catalog.read_text(encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            add_product(item, self.catalog)
        self.assertEqual(self.catalog.read_text(encoding="utf-8"), before)

    def test_next_code_skips_non_numeric(self):
        self.assertEqual(next_code([{"code": "1001"}, {"code": "SKY-9"}]), "1002")


if __name__ == "__main__":
    unittest.main()
