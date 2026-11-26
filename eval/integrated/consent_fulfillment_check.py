"""Can fulfillment / deadline be checked at the payment-consent point? (feasibility only; no model calls)

For validation journeys whose decision point is a payment-consent request (P2 dev sets), look at
  (1) the consent message itself (wallet/system confirm text),
  (2) the last checkout-state tool result before t (update/create/start checkout, checkout sessions,
      fulfillment choice, cart-mandate request),
and count whether they carry the fulfillment method (shipping / pickup) and a selected delivery option whose
text states a time ("Standard (4-7 days)", "Express (1-2 days)").
Output: results/integrated_dev_20261126/consent_fulfillment_check.json
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "m1_v2"))
sys.path.insert(0, str(ROOT / "eval" / "e_m1"))
import diagnose as D  # noqa: E402
from recompute_truncated import decision_point  # noqa: E402

DEV = ROOT / "results" / "integrated_dev_20261126"
CHECKOUT_TOOLS = {"create_checkout", "update_checkout", "get_checkout", "start_checkout", "choose_fulfillment",
                  "set_shipping_address", "create_checkout_session", "update_checkout_session", "get_checkout_session",
                  "request_cart_mandate", "create_checkout_mandate"}
DAYS = re.compile(r"\(\s*\d+\s*-\s*\d+\s*(?:business\s+)?days?\s*\)|\b\d+\s*-\s*\d+\s*(?:business\s+)?days\b", re.I)


def dec(s):
    try:
        o = json.loads(s or "null")
        while isinstance(o, str):
            o = json.loads(o)
        return o
    except (json.JSONDecodeError, TypeError):
        return None


def find(o, keys, out):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in keys:
                out.append((k, v))
            find(v, keys, out)
    elif isinstance(o, list):
        for v in o:
            find(v, keys, out)


def main():
    rows = [json.loads(l) for s in ("V1", "V3", "V2") for l in (DEV / f"extract_{s}.jsonl").read_text(encoding="utf-8").splitlines()]
    cons = [r for r in rows if r["t_kind"] == "consent_request"]
    T = D.load_turns({r["episode_id"] for r in cons}, splits=("validation",))
    c = Counter()
    for r in cons:
        t = T[r["episode_id"]]
        cut, _ = decision_point(t)
        c["consent_journeys"] += 1
        msg = [x for x in t if x["actor"] == "system" and x["kind"] == "message" and x["seq"] <= cut + 1]
        mtext = (msg[-1]["text"] or "") if msg else ""
        c["consent_message_mentions_fulfillment"] += bool(re.search(r"\b(ship|deliver|pickup|pick up|collect)\w*", mtext, re.I))
        c["consent_message_mentions_days"] += bool(DAYS.search(mtext))
        res = [x for x in t if x["kind"] == "tool_result" and x["tool"] in CHECKOUT_TOOLS and x["seq"] < cut]
        if not res:
            c["no_checkout_state_before_t"] += 1
            continue
        last = dec(res[-1]["result"])
        raw = json.dumps(last) if last is not None else ""
        found = []
        find(last, {"type", "method", "selected_option", "selected_option_id", "selected_fulfillment_option_id",
                    "fulfillment_option_id", "expectations", "fulfillment_options", "options"}, found)
        method = any(k in ("type", "method") and str(v).lower() in ("shipping", "pickup", "delivery", "pick_up", "shipping_method")
                     for k, v in found)
        selected = any(k in ("selected_option", "selected_option_id", "selected_fulfillment_option_id", "fulfillment_option_id")
                       and v not in (None, "", []) for k, v in found) or "expectations" in raw
        c["checkout_state_has_fulfillment_method"] += method
        c["checkout_state_has_selected_option"] += selected
        c["checkout_state_has_delivery_days_text"] += bool(DAYS.search(raw))
        c["checkout_state_selected_option_with_days"] += bool(selected and DAYS.search(raw))
        c[f"last_tool:{res[-1]['tool']}"] += 1
    out = {"note": __doc__.split("\n\n")[0], "counts": dict(sorted(c.items()))}
    (DEV / "consent_fulfillment_check.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
