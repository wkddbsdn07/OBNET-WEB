"""Read-only check: python3 -B -m obnote_shorts.preflight REVIEW.json CODE PURPOSE.

REVIEW is workspace-relative; asset and evidence paths are relative to REVIEW's
folder. Supply only trusted operator review files. Exit 0: record passes for the
specified purpose, 1: denied, 2: invalid invocation. Never renders or publishes.
"""
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from .media_permissions import validate_media

ROOT = Path(__file__).resolve().parents[1]
MAX_RECORD = 64 * 1024


def unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise ValueError('Duplicate review field')
        fields[key] = value
    return fields


def main(args):
    if args == ['--help']:
        print(__doc__)
        return 0
    if len(args) != 3 or args[2] not in ('preview', 'distribution'):
        print('Usage: preflight WORKSPACE_RELATIVE_REVIEW.json CODE preview|distribution', file=sys.stderr)
        return 2
    name, code, purpose = args
    try:
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or relative.suffix != '.json':
            raise ValueError('Expected a relative JSON path')
        path = ROOT
        for part in relative.parts:
            path /= part
            if path.is_symlink():
                raise ValueError('Symlink not accepted')
        if not path.is_file():
            raise ValueError('Expected a regular file')
        with path.open('rb') as stream:
            raw = stream.read(MAX_RECORD + 1)
        if len(raw) > MAX_RECORD:
            raise ValueError('Review too large')
        record = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_fields)
        approval = validate_media(record, workspace=path.parent, product_code=code,
                                  purpose=purpose, now=datetime.now(UTC))
    except (ValueError, OSError, RecursionError):
        print(json.dumps({'decision': 'deny', 'purpose': purpose}))
        return 1
    print(json.dumps({'decision': 'allow', 'purpose': purpose,
                      'test_material': approval.is_test_material}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
