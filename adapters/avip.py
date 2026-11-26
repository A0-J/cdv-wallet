"""Thin adapter over A-VIP decision-basis binding (third_party/avip_defense/binding/mechanism).

The A-VIP package is used unmodified. Its location defaults to the pinned submodule and can be
overridden with the CDV_AVIP_BINDING environment variable (path to the `binding` folder).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_DEFAULT = Path(__file__).resolve().parents[1] / "third_party" / "avip_defense" / "binding"


def _load():
    path = Path(os.environ.get("CDV_AVIP_BINDING", _DEFAULT))
    if not (path / "mechanism" / "__init__.py").exists():
        raise ImportError(f"A-VIP binding not found at {path}; add the submodule or set CDV_AVIP_BINDING")
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    import mechanism  # noqa: E402  (A-VIP package)
    return mechanism


M = _load()


def capture(offers: list[dict]):
    """offers: dicts with cart_id, seller, label (raw text as returned), amount, currency."""
    return M.build_capture(offers)


def claims(cap):
    """Cross-seller claim attribution with A-LEX v1 (code only) and A-VIP's authority rule."""
    return M.attribute_and_rule(cap, M.ALex())


def record(cap, chosen_key, policy: str = "STRIP", user_confirmed: bool = False):
    cl = claims(cap)
    return M.build_record(cap, cl, chosen_key, policy, "A-LEX v1", user_confirmed=user_confirmed)


def verify(r_body: dict, cap, strict: bool = True):
    """Run A-VIP's V1-V8 (V7 with A-LEX re-attribution). Returns (ok, codes)."""
    v = M.verify(r_body, cap, mode="STRICT" if strict else "DEFAULT", attributor=M.ALex())
    return v.ok, v.codes()


def record_hash(r_body: dict) -> str:
    return M.record_hash(r_body)
