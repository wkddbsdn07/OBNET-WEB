import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from catalog_http import fetch_json


class CatalogHttpTest(unittest.TestCase):
    def test_retries_temporary_server_error(self):
        temporary = HTTPError("https://example.invalid", 503, "Unavailable", {}, io.BytesIO(b"{}"))
        payload = io.BytesIO(json.dumps([{"code": "1001"}]).encode("utf-8"))
        delays = []
        with patch("catalog_http.urlopen", side_effect=[temporary, payload]) as fetch:
            value = fetch_json("https://example.invalid", sleep=delays.append)
        self.assertEqual(value[0]["code"], "1001")
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(delays, [1])

    def test_permission_errors_never_retry(self):
        denied = HTTPError("https://example.invalid", 403, "Forbidden", {}, io.BytesIO(b"{}"))
        with patch("catalog_http.urlopen", side_effect=denied) as fetch:
            with self.assertRaises(HTTPError):
                fetch_json("https://example.invalid", sleep=lambda _: None)
        self.assertEqual(fetch.call_count, 1)

    def test_temporary_network_error_retry_exhaustion(self):
        with patch("catalog_http.urlopen", side_effect=URLError("offline")) as fetch:
            with self.assertRaises(URLError):
                fetch_json("https://example.invalid", attempts=3, sleep=lambda _: None)
        self.assertEqual(fetch.call_count, 3)


if __name__ == "__main__":
    unittest.main()
