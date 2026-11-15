import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from manage_products import edit_payload, product_payload, request_supabase


class ManageProductsTest(unittest.TestCase):
    def test_edit_can_clear_price_and_url(self):
        self.assertEqual(edit_payload("price", ""), {"price": None})
        self.assertEqual(edit_payload("purchase_url", ""), {"purchase_url": None})

    def test_boolean_fields(self):
        self.assertEqual(edit_payload("published", "false"), {"published": False})
        self.assertEqual(edit_payload("is_demo", "true"), {"is_demo": True})
        with self.assertRaises(ValueError):
            edit_payload("published", "maybe")

    def test_features(self):
        self.assertEqual(edit_payload("features", "Fast | Quiet"),
                         {"features": ["Fast", "Quiet"]})

    def test_unapproved_url_refused(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            edit_payload("purchase_url", "http://unsafe.example")

    def test_demo_removes_purchase_and_price(self):
        env = {
            "PRODUCT_NAME": "Test desk",
            "PRODUCT_CATEGORY": "DESK TECH",
            "PRODUCT_DESCRIPTION": "Test listing",
            "PRODUCT_PRICE": "15.00",
            "PRODUCT_PURCHASE_URL": "https://example.com/seller",
            "PRODUCT_IS_DEMO": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            result = product_payload()
        self.assertIsNone(result["purchase_url"])
        self.assertIsNone(result["price"])
        self.assertTrue(result["published"])
        self.assertTrue(result["is_demo"])

    def test_secret_required_no_network_call(self):
        with self.assertRaisesRegex(ValueError, "Missing GitHub Actions secret"):
            request_supabase("", "add", None, {"name": "Test"})

    def test_duplicate_name_returns_clear_error(self):
        import io
        import json
        from urllib.error import HTTPError

        response = {"code": "23505",
                    "message": 'duplicate key value violates unique constraint "obnote_products_name_unique"'}
        failure = HTTPError("https://example.invalid", 409, "Conflict", {},
                            io.BytesIO(json.dumps(response).encode("utf-8")))
        with patch("manage_products.urlopen", side_effect=failure):
            with self.assertRaisesRegex(ValueError, "DUPLICATE NAME"):
                request_supabase("sb_secret_test", "add", None, {"name": "Existing"})

    def test_duplicate_seller_url_returns_clear_error(self):
        import io
        import json
        from urllib.error import HTTPError

        response = {"code": "23505",
                    "message": 'duplicate key value violates unique constraint "obnote_products_seller_url_unique"'}
        failure = HTTPError("https://example.invalid", 409, "Conflict", {},
                            io.BytesIO(json.dumps(response).encode("utf-8")))
        with patch("manage_products.urlopen", side_effect=failure):
            with self.assertRaisesRegex(ValueError, "DUPLICATE SELLER LINK"):
                request_supabase("sb_secret_test", "add", None,
                                 {"purchase_url": "https://example.invalid/item"})

    def test_stock_status_validation(self):
        from manage_products import edit_payload
        self.assertEqual(edit_payload("stock_status", "out_of_stock"),
                         {"stock_status": "out_of_stock"})
        with self.assertRaisesRegex(ValueError, "Stock"):
            edit_payload("stock_status", "guaranteed_available")

    def test_demo_never_claims_stock(self):
        from manage_products import product_payload
        environment = {
            "PRODUCT_NAME": "Demo Lamp",
            "PRODUCT_DESCRIPTION": "Demo only",
            "PRODUCT_STOCK_STATUS": "in_stock",
            "PRODUCT_IS_DEMO": "true",
        }
        with patch.dict(os.environ, environment, clear=True):
            data = product_payload()
        self.assertEqual(data["stock_status"], "unknown")

    def test_unknown_field_not_allowed(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            edit_payload("code", "9999")


if __name__ == "__main__":
    unittest.main()
