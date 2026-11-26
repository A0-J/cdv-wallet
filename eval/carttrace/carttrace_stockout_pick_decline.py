"""Addendum to carttrace_field_check.py (read-only, no model calls).

Researcher's observation (2026-11-26): in CartTrace an item goes out of stock, the
shopper picks something else, and then refuses at the final payment step.

Counts, per stockout setting, journeys where a shopper "pick" turn is followed by a
shopper "decline" turn at the checkout/payment stage. Regexes are rough and were
fixed in this script before counting; no text is written to the output.

Usage:
    python -I eval/carttrace/carttrace_stockout_pick_decline.py --out results/cdv_wallet_field_check_20261126/addendum1.json
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import re
from pathlib import Path

import pyarrow.parquet as pq

DATA = Path(r"C:/ct/kit/dataset/data")

DECLINE = re.compile(
    r"(not (the item|what) i (asked|requested|wanted)|isn.t what i asked|don.t place|do not place|"
    r"stop the order|refrain from placing|cancel (the|my) order|don.t (want|proceed)|hold off|decline)", re.I)
PICK = re.compile(
    r"(i.ll go with|i will proceed with|go with option|option \d|i.d rather|i.ll take|let.s go with|that one)", re.I)
ACCEPT = re.compile(
    r"^(yes|yep|sure|ok|okay|sounds good|go ahead|i (do )?confirm|please proceed|place the order)", re.I)


def checkout_fault_kinds(raw: str | None) -> str:
    d = json.loads(raw or "{}") or {}
    return "+".join(sorted({f.get("kind", "?") for f in (d.get("faults") or [])})) or "-"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows: list[dict] = []
    for f in sorted(glob.glob(str(DATA / "messages" / "*" / "*.parquet"))):
        rows += pq.read_table(f, columns=["episode_id", "hidden_spec", "split", "sub_kind", "checkout_faults",
                                          "transaction_state", "outcome_class"]).to_pylist()

    groups: dict[str, dict[str, dict]] = {"browse_stockout": {}, "checkout_stockout": {}, "checkout_reprice": {}}
    for r in rows:
        if any(f.get("kind") == "stockout" for f in (json.loads(r["hidden_spec"]).get("faults") or [])):
            groups["browse_stockout"][r["episode_id"]] = r
        if r["sub_kind"] == "checkout":
            k = checkout_fault_kinds(r["checkout_faults"])
            if k == "stockout":
                groups["checkout_stockout"][r["episode_id"]] = r
            elif k == "reprice":
                groups["checkout_reprice"][r["episode_id"]] = r
    wanted = set().union(*[set(g) for g in groups.values()])

    turns: dict[str, list[dict]] = collections.defaultdict(list)
    for f in sorted(glob.glob(str(DATA / "turns" / "*.parquet"))):
        for x in pq.read_table(f, columns=["episode_id", "seq", "stage", "actor", "text"],
                               filters=[("actor", "=", "shopper")]).to_pylist():
            if x["episode_id"] in wanted:
                turns[x["episode_id"]].append(x)

    out: dict = {"model_calls": 0, "note": "regex counts, rough; first shopper turn excluded", "groups": {}}
    for name, g in groups.items():
        c = collections.Counter()
        by_split = collections.Counter()
        pd_states = collections.Counter()
        for ep, r in g.items():
            t = sorted(turns.get(ep, []), key=lambda z: z["seq"])[1:]
            picks = [i for i, x in enumerate(t) if PICK.search(x["text"] or "")]
            declines = [i for i, x in enumerate(t)
                        if x["stage"] in ("checkout", "payment") and DECLINE.search(x["text"] or "")]
            accepts = [i for i, x in enumerate(t)
                       if x["stage"] in ("checkout", "payment") and ACCEPT.search((x["text"] or "").strip())]
            c["journeys"] += 1
            c["has_pick"] += bool(picks)
            c["has_decline_at_checkout_or_payment"] += bool(declines)
            c["has_accept_at_checkout_or_payment"] += bool(accepts)
            pd = bool(picks and declines and min(picks) < max(declines))
            c["pick_then_decline"] += pd
            if pd:
                by_split[r["split"]] += 1
                pd_states[f'{r["transaction_state"]}/{r["outcome_class"]}'] += 1
        out["groups"][name] = {
            "counts": dict(c),
            "journeys_by_split": dict(collections.Counter(r["split"] for r in g.values())),
            "pick_then_decline_by_split": dict(by_split),
            "pick_then_decline_state_outcome": dict(pd_states.most_common()),
            "transaction_state": dict(collections.Counter(r["transaction_state"] for r in g.values()).most_common()),
        }
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, v in out["groups"].items():
        print(name, v["counts"], "| pick->decline by split", v["pick_then_decline_by_split"])


if __name__ == "__main__":
    main()
