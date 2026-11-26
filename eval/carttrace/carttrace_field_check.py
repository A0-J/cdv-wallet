"""CDV-Wallet feasibility check on CartTrace-100k (read-only, no model calls).

Question: can CartTrace supply (a) legitimate in-dialogue condition changes and
(b) a per-turn gold condition ledger for evaluating M1?

Reads the local copy under C:\\ct (never committed). Writes counts only; no
dialogue text, product text or persona text is written to the output.

Usage:
    python -I eval/carttrace/carttrace_field_check.py --out results/cdv_wallet_field_check_20261126/summary.json
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
SPLITS = ["train", "validation", "test_cross_store", "test_cross_template"]
TURN_SPLITS = ["validation", "test_cross_store", "test_cross_template"]

STOP = {"i", "i'd", "the", "a", "it", "to", "my", "in", "is", "and", "of", "like",
        "please", "want", "be", "for", "me"}
REVEAL_OVERLAP = 0.6

# Rough, pre-declared regex buckets for non-opening shopper turns (first match wins).
TURN_TYPES = [
    ("delegate", r"go with whatever|whatever (fits|option)|you (choose|pick|decide)|up to you|not sure about that"),
    ("pick_shown", r"\b(go with|i'll take|i'd like the|the (first|second|third|last) one|that one)\b"),
    ("reject", r"none of (those|these)|not what i|doesn't work|don't want"),
    ("confirm", r"^(yes|yep|sure|ok|okay|sounds good|go ahead|confirm)"),
]
# Words that would signal a true revision (relax / override / revoke).
REVISION = re.compile(
    r"\b(changed my mind|on second thought|scratch that|never ?mind|instead of|"
    r"no longer|not anymore|actually,? (make|change|i'd rather)|raise (the|my) budget|"
    r"increase (the|my) budget|forget (about )?the)\b", re.I)


def tok(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9$.]+", s.lower())) - STOP


def load_messages(split: str) -> list[dict]:
    rows: list[dict] = []
    cols = ["episode_id", "hidden_spec", "template_family", "kind", "sub_kind",
            "outcome_class", "licence", "source_catalog"]
    for f in sorted(glob.glob(str(DATA / "messages" / "*" / f"{split}-*.parquet"))):
        rows += pq.read_table(f, columns=cols).to_pylist()
    return rows


def load_shopper_turns(split: str) -> dict[str, list[tuple[int, str, str | None]]]:
    out: dict[str, list] = collections.defaultdict(list)
    for f in sorted(glob.glob(str(DATA / "turns" / f"{split}-*.parquet"))):
        t = pq.read_table(f, columns=["episode_id", "actor", "seq", "text", "wording"],
                          filters=[("actor", "=", "shopper")])
        for x in t.to_pylist():
            out[x["episode_id"]].append((x["seq"], x["text"] or "", x["wording"]))
    return out


def spec_counts(rows: list[dict]) -> dict:
    src = collections.Counter()
    ops = collections.Counter()
    fields_on_ask = collections.Counter()
    forgets = 0
    stockout = collections.Counter()
    stockout_outcome = collections.Counter()
    change_keys = collections.Counter()
    for r in rows:
        h = json.loads(r["hidden_spec"])
        for k in h:
            if re.search(r"chang|revis|switch|update|later|schedule|pivot", k, re.I):
                change_keys[k] += 1
        for p in h.get("predicates") or []:
            src[p.get("source")] += 1
            ops[p.get("op")] += 1
            if p.get("source") == "on_ask":
                fields_on_ask[p.get("field")] += 1
            if "forgets" in p:
                forgets += 1
        if any(f.get("kind") == "stockout" for f in (h.get("faults") or [])):
            stockout[r["template_family"]] += 1
            stockout_outcome[r["outcome_class"]] += 1
    return {
        "journeys": len(rows),
        "predicate_source": dict(src),
        "predicate_op": dict(ops.most_common()),
        "on_ask_fields": dict(fields_on_ask.most_common()),
        "predicates_with_forgets_flag": forgets,
        "hidden_spec_keys_suggesting_scheduled_change": dict(change_keys),
        "stockout_fault_journeys_by_template": dict(stockout),
        "stockout_fault_outcomes": dict(stockout_outcome),
        "template_family": dict(collections.Counter(r["template_family"] for r in rows).most_common()),
        "kind": dict(collections.Counter(r["kind"] for r in rows)),
        "licence": dict(collections.Counter(r["licence"] for r in rows).most_common()),
    }


def turn_counts(rows: list[dict], shopper: dict) -> dict:
    per_journey = collections.Counter(len(v) for v in shopper.values())
    types = collections.Counter()
    wording = collections.Counter()
    revision = 0
    for turns in shopper.values():
        for seq, text, w in sorted(turns)[1:]:
            wording[str(w)] += 1
            types[next((n for n, pt in TURN_TYPES if re.search(pt, text, re.I)), "other")] += 1
            if REVISION.search(text):
                revision += 1
    total = hit = 0
    hit_exact_wording = total_exact_wording = 0
    for r in rows:
        later = sorted(shopper.get(r["episode_id"], []))[1:]
        h = json.loads(r["hidden_spec"])
        for p in h.get("predicates") or []:
            if p.get("source") != "on_ask" or not p.get("say"):
                continue
            a = tok(p["say"])
            best = max([len(a & tok(tx)) / max(1, len(a)) for _, tx, _ in later] or [0.0])
            total += 1
            hit += best >= REVEAL_OVERLAP
            exact = [tx for _, tx, w in later if w is None]
            if exact:
                total_exact_wording += 1
                hit_exact_wording += any(p["say"].lower() in tx.lower() for tx in exact)
    return {
        "shopper_turns_per_journey": dict(sorted(per_journey.items())),
        "non_opening_shopper_turns": sum(types.values()),
        "non_opening_turn_type_regex": dict(types.most_common()),
        "non_opening_wording": dict(wording.most_common()),
        "turns_matching_revision_regex": revision,
        "on_ask_predicates": total,
        "on_ask_found_by_token_overlap": hit,
        "on_ask_overlap_threshold": REVEAL_OVERLAP,
        "on_ask_with_unparaphrased_later_turn": total_exact_wording,
        "on_ask_say_substring_in_unparaphrased_turn": hit_exact_wording,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    result: dict = {"source": "CartTrace-100k local copy C:/ct (see C:/ct/PROVENANCE.txt)",
                    "model_calls": 0, "spec": {}, "turns": {}}
    for s in SPLITS:
        rows = load_messages(s)
        result["spec"][s] = spec_counts(rows)
        if s in TURN_SPLITS:
            result["turns"][s] = turn_counts(rows, load_shopper_turns(s))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({s: {"journeys": result["spec"][s]["journeys"],
                          "stockout": sum(result["spec"][s]["stockout_fault_journeys_by_template"].values())}
                      for s in SPLITS}))
    for s in TURN_SPLITS:
        t = result["turns"][s]
        print(s, "revision-regex", t["turns_matching_revision_regex"], "of", t["non_opening_shopper_turns"],
              "| on_ask overlap", t["on_ask_found_by_token_overlap"], "/", t["on_ask_predicates"],
              "| exact", t["on_ask_say_substring_in_unparaphrased_turn"], "/", t["on_ask_with_unparaphrased_later_turn"])


if __name__ == "__main__":
    main()
