"""Canonical JSON, hashing and signatures.

Canonicalisation is the same as A-VIP binding (binding/mechanism/record.py): sort_keys,
separators (",", ":"), UTF-8, no ASCII escaping.

Signatures
  * ECDSA P-256 with SHA-256 (public-key; the verifier needs only the public key). This is the
    scheme AP2 mandates use according to the A-VIP paper (section 2). Default since 2026-11-26.
  * HMAC-SHA256 is kept only as a labelled mock (`MockHmacKey`) for the "no public-key signature"
    ablation. It proves nothing to a third party: the verifier must hold the same secret.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec


def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(obj) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


# ---------------------------------------------------------------- ECDSA P-256 (default)

def new_signing_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


def public_of(key) -> ec.EllipticCurvePublicKey:
    return key.public_key()


@dataclass(frozen=True)
class MockHmacKey:
    """Ablation only: symmetric mock. Not a digital signature."""
    secret: bytes


def sign(key, obj) -> str:
    """key: ECDSA private key (default) or MockHmacKey (ablation)."""
    if isinstance(key, MockHmacKey):
        return "hmac:" + hmac.new(key.secret, canonical_json(obj), hashlib.sha256).hexdigest()
    if isinstance(key, ec.EllipticCurvePrivateKey):
        return "es256:" + key.sign(canonical_json(obj), ec.ECDSA(hashes.SHA256())).hex()
    raise TypeError("unsupported signing key")


def verify(key, obj, sig: str) -> bool:
    """key: ECDSA public key (default) or the same MockHmacKey (ablation)."""
    sig = sig or ""
    if isinstance(key, MockHmacKey):
        good = "hmac:" + hmac.new(key.secret, canonical_json(obj), hashlib.sha256).hexdigest()
        return hmac.compare_digest(good, sig)
    if isinstance(key, ec.EllipticCurvePublicKey):
        if not sig.startswith("es256:"):
            return False
        try:
            key.verify(bytes.fromhex(sig[6:]), canonical_json(obj), ec.ECDSA(hashes.SHA256()))
            return True
        except (InvalidSignature, ValueError):
            return False
    raise TypeError("unsupported verification key")


# backwards-compatible names used by phase-1 code
def hmac_sign(key, obj) -> str:
    return sign(key if not isinstance(key, bytes) else MockHmacKey(key), obj)


def hmac_verify(key, obj, sig: str) -> bool:
    return verify(key if not isinstance(key, bytes) else MockHmacKey(key), obj, sig)
