"""Run the deterministic M1 verifier (cdv/m1.py) on G1 cases and compare with the gold verdicts.

This is a functional check of the verifier against cases whose proposals are simulated (correct
or faulty by construction). It is not an effectiveness result: the templates and the rules were
written by the same author, and a real extractor's proposals are not involved.

Usage: python -I eval/templates/g1_check.py --split dev|eval
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cdv.m1 import ChangeOp, Entry, Ledger, UserTurn, verify_turn  # noqa: E402

IN = Path(r"C:/ct/runs/cdv_wallet/generated/G1")


def ent(d):
    if d is None:
        return None
    v = d["value"]
    return Entry(d["id"], d["field"], tuple(v) if isinstance(v, list) else v, d["strength"], tuple(d["basis"]), d["scope"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "eval"], required=True)
    a = ap.parse_args()
    res = defaultdict(Counter)
    mismatches = []
    for line in (IN / f"{a.split}.jsonl").read_text(encoding="utf-8").splitlines():
        c = json.loads(line)
        turns = [UserTurn(t["turn_id"], t["seq"], t["text"]) for t in c["user_turns"]]   # external_texts never passed
        prev = Ledger(c["prev_ledger"]["version"], tuple(ent(e) for e in c["prev_ledger"]["entries"]))
        ops = [ChangeOp(o["op"], o["entry_id"], ent(o["new"]), tuple(o["cited"])) for o in c["proposed_ops"]]
        r = verify_turn(prev, ops, turns)
        got = {}
        if "gold_vc" in c["gold"]:
            got["gold_vc"] = r.change_findings[0].status
        if "gold_vx" in c["gold"]:
            got["gold_vx"] = next(f.status for f in r.findings if f.check == "V-X")
        if "gold_omission" in c["gold"]:
            got["gold_omission"] = next(f.status for f in r.findings if f.detail == "omission scan")
        for k, g in c["gold"].items():
            ok = got[k] == g
            res[c["template_id"]]["n"] += 1
            res[c["template_id"]]["match"] += ok
            if not ok:
                mismatches.append({"case_id": c["case_id"], "check": k, "gold": g, "got": got[k],
                                   "findings": [(f.check, f.status, f.codes) for f in r.change_findings + r.findings]})
    out = {"split": a.split, "model_calls": 0, "kind": "functional check (simulated proposals)",
           "by_template": {k: dict(v) for k, v in sorted(res.items())},
           "total": {"n": sum(v["n"] for v in res.values()), "match": sum(v["match"] for v in res.values())},
           "mismatches": mismatches}
    p = ROOT / "results" / "g1_templates_20261126" / f"check_{a.split}.json"
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(a.split, out["total"], "mismatches", len(mismatches))
    for m in mismatches[:8]:
        print("  ", m["case_id"], m["check"], m["gold"], "->", m["got"], m["findings"][:3])


if __name__ == "__main__":
    main()
