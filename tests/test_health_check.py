import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from health_check import check_page, check_public_catalog


class FakeResponse:
    status = 200

    def __init__(self, html):
        self.html = html

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.html[:limit].encode("utf-8")


class PublicHealthTest(unittest.TestCase):
    def test_homepage_requires_real_search_form(self):
        with patch("health_check.urlopen", return_value=FakeResponse(
            '<html>OBNOTE<form id="searchForm"></form></html>'
        )):
            self.assertTrue(check_page("https://obnote.vercel.app/", ("OBNOTE", 'id="searchForm"')))

    def test_placeholder_does_not_count_as_real_site(self):
        with patch("health_check.urlopen", return_value=FakeResponse(
            "<html><h1>OBNOTE</h1><p>Placeholder</p></html>"
        )):
            with self.assertRaisesRegex(RuntimeError, "searchForm"):
                check_page("https://obnote.vercel.app/", ("OBNOTE", 'id="searchForm"'))

    def test_public_products_no_writes(self):
        with patch("health_check.fetch_json", return_value=[{"code": "1001"}]) as fetch:
            self.assertEqual(check_public_catalog("sb_publishable_test"), 1)
        self.assertEqual(fetch.call_count, 1)
        self.assertIn("published=eq.true", fetch.call_args.args[0].full_url)

    def test_secret_key_not_accepted_in_public_monitor(self):
        with self.assertRaisesRegex(ValueError, "public read-only"):
            check_public_catalog("sb_secret_test")


if __name__ == "__main__":
    unittest.main()
