"""M1 omission scan (V-B) on real CartTrace user turns. No model calls.

Plan: results/omission_realtext_20261126/PLAN.md (written before computing).
Usage: python -I eval/carttrace/omission_realtext.py --split validation|test_cross_store
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cdv.m1 import Entry, Ledger, UserTurn, scan_omissions  # noqa: E402

DATA = Path(r"C:/ct/kit/dataset/data")
OUTDIR = ROOT / "results" / "omission_realtext_20261126"
FIELD_OF_CODE = {"OMITTED_BUDGET": "budget_max", "OMITTED_SUBSTITUTE": "substitute", "OMITTED_QUANTITY": "quantity",
                 "OMITTED_BRAND_IN": "brand_in", "OMITTED_BRAND_OUT": "brand_out", "OMITTED_BUNDLE": "bundle_all",
                 "OMITTED_DEADLINE": "deadline_days", "OMITTED_FULFILLMENT": "fulfillment"}


def gold(h: dict):
    entries, stated, brands, items = [], set(), set(), {}
    for i, p in enumerate(h.get("predicates") or []):
        if p.get("source") not in ("stated", "on_ask"):
            continue
        op, v, eid = p.get("op"), p.get("value"), f"p{i}"
        e = None
        if op == "max_price" and isinstance(v, dict) and "amount" in v:
            e = Entry(eid, "budget_max", round(v["amount"] / 100, 2), basis=("u0",))
        elif op == "count":
            try:
                e = Entry(eid, "quantity", int(v), basis=("u0",))
            except (TypeError, ValueError):
                e = None
        elif op == "all_of" and isinstance(v, list):
            ids = tuple(str(x.get("product_id")) for x in v)
            for x in v:
                t = (x.get("title") or "").split()
                items[str(x.get("product_id"))] = " ".join(t[:3])
            e = Entry(eid, "bundle_all", ids, basis=("u0",))
        elif op == "brand":
            e = Entry(eid, "brand_in", (str(v),), basis=("u0",))
            brands.add(str(v))
        elif op == "excludes":
            e = Entry(eid, "brand_out", (str(v),), basis=("u0",))
            brands.add(str(v))
        elif op == "prefer":
            e = Entry(eid, "substitute", None, basis=("u0",), scope={"named": False, "then": {}})
        if e is not None:
            entries.append(e)
            if p.get("source") == "stated":
                stated.add(e.field)
    f = (h.get("buyer") or {}).get("fulfillment") or {}
    if f.get("source") in ("stated", "on_ask"):
        kind = "pickup" if f.get("value") == "pickup" else "ship"
        entries.append(Entry("ful", "fulfillment", kind, basis=("u0",)))
        if f.get("source") == "stated":
            stated.add("fulfillment")
        if f.get("deadline_days"):
            entries.append(Entry("dl", "deadline_days", int(f["deadline_days"]), basis=("u0",)))
            if f.get("source") == "stated":
                stated.add("deadline_days")
    return entries, stated, sorted(brands), items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["validation", "test_cross_store"], required=True)
    ap.add_argument("--tag", default="", help="suffix for the output file (never overwrite earlier summaries)")
    a = ap.parse_args()
    plan_sha = hashlib.sha256((OUTDIR / "PLAN.md").read_bytes()).hexdigest()
    msgs = []
    for f in sorted(glob.glob(str(DATA / "messages" / "*" / f"{a.split}-*.parquet"))):
        msgs += pq.read_table(f, columns=["episode_id", "hidden_spec", "kind"]).to_pylist()
    msgs = [m for m in msgs if m["kind"] == "baseline"]
    turns = defaultdict(list)
    for f in sorted(glob.glob(str(DATA / "turns" / f"{a.split}-*.parquet"))):
        for x in pq.read_table(f, columns=["episode_id", "seq", "actor", "text"], filters=[("actor", "=", "shopper")]).to_pylist():
            turns[x["episode_id"]].append(UserTurn(f"s{x['seq']}", x["seq"], x["text"] or ""))
    fa = Counter()          # false-alarm journeys per field (complete gold)
    fa_examples = defaultdict(list)
    det_n, det_k = Counter(), Counter()
    times = []
    n_j = 0
    for m in msgs:
        h = json.loads(m["hidden_spec"])
        entries, stated, brands, items = gold(h)
        ut = sorted(turns.get(m["episode_id"], []), key=lambda t: t.seq)
        if not entries or not ut:
            continue
        n_j += 1
        t0 = time.perf_counter()
        f = scan_omissions(Ledger(1, tuple(entries)), ut, known_brands=brands, known_items=items)
        times.append(time.perf_counter() - t0)
        fields = {FIELD_OF_CODE[c.split(":")[0]] for c in f.codes}
        for fl in fields:
            fa[fl] += 1
            if len(fa_examples[fl]) < 15:
                fa_examples[fl].append(m["episode_id"])
        for fl in stated:
            kept = tuple(e for e in entries if e.field != fl)
            g = scan_omissions(Ledger(1, kept), ut, known_brands=brands, known_items=items)
            det_n[fl] += 1
            det_k[fl] += any(FIELD_OF_CODE[c.split(":")[0]] == fl for c in g.codes)
    out = {"plan_sha256": plan_sha, "split": a.split, "model_calls": 0, "journeys": n_j,
           "post_hoc": a.split == "test_cross_store",
           "false_alarm_journeys_by_field": dict(fa),
           "false_alarm_rate_by_field_pct": {k: round(100 * v / n_j, 2) for k, v in fa.items()},
           "false_alarm_example_episode_ids": dict(fa_examples),
           "detection_by_field": {k: {"n": det_n[k], "detected": det_k[k],
                                      "pct": round(100 * det_k[k] / det_n[k], 1)} for k in sorted(det_n)},
           "latency_ms": {"median": round(1000 * statistics.median(times), 3),
                          "p95": round(1000 * sorted(times)[int(0.95 * len(times)) - 1], 3)},
           "plan_sha256_at_end": hashlib.sha256((OUTDIR / "PLAN.md").read_bytes()).hexdigest()}
    name = f"summary_{a.split}{'_' + a.tag if a.tag else ''}.json"
    assert not (OUTDIR / name).exists(), f"refusing to overwrite {name}"
    out["tag"] = a.tag
    (OUTDIR / name).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: out[k] for k in ("journeys", "false_alarm_rate_by_field_pct", "detection_by_field", "latency_ms")}))


if __name__ == "__main__":
    main()
