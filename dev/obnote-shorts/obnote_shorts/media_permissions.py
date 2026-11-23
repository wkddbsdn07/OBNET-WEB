"""Fail-closed validation of operator-reviewed local media records.

This checks a record's integrity and scope, NOT whether a legal grant is genuine.
Records must come from a trusted review workflow, never directly from a seller
page or untrusted ingestion. No network, credentials, or paid services are used.
Revalidate before rendering; this module alone does not enforce a render gate.
"""
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit


class PermissionDenied(ValueError):
    """Media cannot be used for the requested purpose."""


@dataclass(frozen=True)
class MediaApproval:
    product_code: str
    purpose: str
    asset_path: Path
    asset_sha256: str
    evidence_path: Path
    evidence_sha256: str
    source_url: str
    reviewer: str
    is_test_material: bool
    attribution_text: str


def _text(record, key):
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PermissionDenied(f"Missing or invalid {key}")
    return value


def _timestamp(value):
    if not isinstance(value, str):
        raise PermissionDenied("Invalid timestamp")
    try:
        stamp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise PermissionDenied("Invalid timestamp") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise PermissionDenied("Timestamp must include timezone")
    return stamp


def _verified_file(root, record, kind):
    name = _text(record, kind + '_path')
    digest = _text(record, kind + '_sha256')
    if re.fullmatch(r'[0-9a-f]{64}', digest) is None:
        raise PermissionDenied(f"Invalid {kind} SHA-256")
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise PermissionDenied(f"Invalid {kind} path")
    path = root
    for component in relative.parts:
        path = path / component
        if path.is_symlink():
            raise PermissionDenied(f"Symlinks forbidden in {kind} path")
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise PermissionDenied(f"Invalid {kind} file")
        with resolved.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != digest:
            raise PermissionDenied(f"{kind} content differs from reviewed hash")
    except (OSError, RuntimeError) as exc:
        raise PermissionDenied(f"Cannot read {kind} file") from exc
    return resolved, digest


def validate_media(record, *, workspace, product_code, purpose, now):
    """Return an immutable approval snapshot or raise PermissionDenied.

    now is a caller-supplied timezone-aware clock reading (injectable for tests).
    Both preview and distribution require reviewed evidence. Distribution also
    rejects test material and requires commercial/editing/redistribution scope.
    This is a minimum technical gate; human review must cover any additional
    grant restrictions. A snapshot is not a signature or a permission to publish.
    """
    if not isinstance(record, dict):
        raise PermissionDenied('Expected a media review record')
    if type(record.get('schema_version')) is not int or record['schema_version'] != 1:
        raise PermissionDenied('Unsupported schema version')
    if purpose not in ('preview', 'distribution'):
        raise PermissionDenied('Unknown usage purpose')
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise PermissionDenied('Current time must include timezone')
    code = _text(record, 'product_code')
    if re.fullmatch(r'[A-Za-z0-9-]{1,24}', code) is None or code != product_code:
        raise PermissionDenied('Product identity mismatch or invalid code')
    source = _text(record, 'source_url')
    try:
        url = urlsplit(source)
        if (url.scheme != 'https' or not url.hostname or url.username is not None
                or url.password is not None or any(c.isspace() for c in source)):
            raise PermissionDenied('Expected credential-free HTTPS provenance')
    except ValueError as exc:
        raise PermissionDenied('Invalid provenance URL') from exc
    for field in ('rights_holder', 'permission_basis', 'reviewer'):
        _text(record, field)
    if record.get('review_status') != 'approved':
        raise PermissionDenied('Permission is not approved')
    reviewed = _timestamp(record.get('reviewed_at'))
    if reviewed > now:
        raise PermissionDenied('Review time is in the future')
    if 'expires_at' not in record:
        raise PermissionDenied('Explicit expiry or null required')
    if record['expires_at'] is not None:
        expiry = _timestamp(record['expires_at'])
        if expiry <= now or expiry <= reviewed:
            raise PermissionDenied('Permission expired or invalid expiry')
    if type(record.get('is_test_material')) is not bool:
        raise PermissionDenied('Explicit test-material boolean required')
    if purpose == 'distribution' and record['is_test_material']:
        raise PermissionDenied('Test material is not distributable')
    uses = record.get('allowed_uses')
    if not isinstance(uses, list) or not all(isinstance(use, str) for use in uses):
        raise PermissionDenied('Explicit allowed-uses list required')
    required = {'preview'} if purpose == 'preview' else {'commercial', 'editing', 'redistribution'}
    if not required.issubset(uses):
        raise PermissionDenied('Permission does not cover requested use')
    if type(record.get('attribution_required')) is not bool:
        raise PermissionDenied('Explicit attribution requirement required')
    attribution = record.get('attribution_text')
    if not isinstance(attribution, str) or (record['attribution_required'] and not attribution.strip()):
        raise PermissionDenied('Missing attribution text')
    try:
        root = Path(workspace).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PermissionDenied('Workspace unavailable') from exc
    asset, asset_hash = _verified_file(root, record, 'asset')
    evidence, evidence_hash = _verified_file(root, record, 'evidence')
    return MediaApproval(code, purpose, asset, asset_hash, evidence, evidence_hash,
                         source, record['reviewer'], record['is_test_material'], attribution)
