"""Small retry helper for Supabase's PUBLIC catalog API (no secret keys).

Only transient errors are retried. 401/403/404 and validation errors fail
immediately, so bad permissions or incorrect codes are never hidden.
"""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

RETRY_CODES = {408, 429, 500, 502, 503, 504}


def fetch_json(request, timeout=25, attempts=3, sleep=None):
    if attempts < 1:
        raise ValueError("At least one request attempt is required")
    sleep = sleep or time.sleep
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code not in RETRY_CODES or attempt == attempts - 1:
                raise
        except (URLError, TimeoutError):
            if attempt == attempts - 1:
                raise
        sleep(min(2 ** attempt, 6))
    raise RuntimeError("Unreachable retry state")
