"""Canonical JSON and hashing.

Same canonicalisation as A-VIP binding (binding/mechanism/record.py): sort_keys,
separators (",", ":"), UTF-8, no ASCII escaping. Keeping the rule identical lets a
combined hash be recomputed by a verifier that already checks A-VIP's record.
"""
from __future__ import annotations

import hashlib
import hmac
import json


def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(obj) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def hmac_sign(key: bytes, obj) -> str:
    """Signature stand-in for the experiment harness.

    HMAC-SHA256 models "only the key holder can produce this value". It is NOT a public-key
    signature: a verifier needs the key. A deployment would use ECDSA P-256 / SD-JWT as in AP2.
    """
    return hmac.new(key, canonical_json(obj), hashlib.sha256).hexdigest()


def hmac_verify(key: bytes, obj, sig: str) -> bool:
    return hmac.compare_digest(hmac_sign(key, obj), sig or "")
