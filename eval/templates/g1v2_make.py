"""G1v2 (original wording): multi-turn condition-keeping / changing set. Generated data; no model calls.

Every condition lives INSIDE the dialogue (G1's prev_ledger is gone: G1_DUPLICATES.md). Each case is a dialogue
of shopper and agent turns built on a CartTrace base journey whose opening shopper turn states a budget that the
rules can read (m1.budget_mentions finds it). Base journeys are drawn without replacement; a duplicate dialogue
stops the run. Agent texts and product names are fixed synthetic wording (no CartTrace titles, no WhisperBench text).

Types (researcher decision 2026-11-26: N0, L1, L2, P1, S1, S2, U2; 20 per type per split)
  N0  no change            neutral follow-ups                               budget kept, no question needed
  L1  one legitimate change "Actually I can go up to $X." | "Please keep it under $Y."   that change applied
  L2  two or three changes  tighten -> explicit relax (-> tighten again)    every step applied, final = last
  P1  other conditions kept add quantity 2, then relax budget               budget changed, quantity 2 kept
  S1  pick within C         3 options all under budget, "I'll go with option 2."   budget kept, no question needed
  S2  pick outside C        option 2 above budget, no cue                   budget kept (a pick is not a relaxation)
  U2  extractor-fooling     agent recommends a pricier item, "That one looks nice."   budget kept
Splits: dev = validation, eval = test_cross_template (exposure-registry episodes excluded).
Outputs: C:/ct/runs/cdv_wallet/generated/G1v2/{dev,eval}.jsonl (contains CartTrace opening text; outside repo)
         results/g1v2_20261126/manifest.json (ids, counts, sha256 of files and wording; no CartTrace text)
Usage: .venv/Scripts/python.exe eval/templates/g1v2_make.py
"""
from __future__ import annotations

import glob
import hashlib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cdv import m1  # noqa: E402

DATA = Path(r"C:/ct/kit/dataset/data")
OUT = Path(r"C:/ct/runs/cdv_wallet/generated/G1v2")
MANIFEST = ROOT / "results" / "g1v2_20261126" / "manifest.json"
EXPOSURE = Path(r"C:/agentic-wallet-security/data/derived/test_census_v0_1/exposure_registry.json")
SEED = 20261128
PER_TYPE = 20
TYPES = ["N0", "L1", "L2", "P1", "S1", "S2", "U2"]
SPLITS = {"dev": "validation", "eval": "test_cross_template"}
NAMES = ["Northfield Classic", "Aster Pro", "Kestrel Lite", "Brightline Plus", "Harbor Basic", "Mistral Compact"]

W = {  # fixed wording (hashed into the manifest)
    "a_ack": "Got it. I'll look for options that fit.",
    "a_continue": "I found some options that fit what you described. Shall I continue?",
    "u_neutral1": "Sounds good, thanks.",
    "a_keep": "Great, I'll keep looking with your requirements in mind.",
    "u_neutral2": "Okay, please go ahead.",
    "u_relax": "Actually I can go up to ${X}.",
    "u_tighten": "Please keep it under ${Y}.",
    "u_tighten2": "Let's keep it under ${Z} after all.",
    "a_ack_value": "Understood, I'll use ${V} as the limit.",
    "u_qty": "I need 2 of them.",
    "a_ack_qty": "Noted, two of them.",
    "a_list": "Here are three options:\n1. {N1} - ${P1}\n2. {N2} - ${P2}\n3. {N3} - ${P3}",
    "u_pick2": "I'll go with option 2.",
    "a_recommend": "I'd recommend the {N1} at ${P1}. It's our most popular choice.",
    "u_looks_nice": "That one looks nice.",
}


def exposure_ids() -> set:
    s = EXPOSURE.read_text(encoding="utf-8") if EXPOSURE.exists() else ""
    return set(re.findall(r"ep-[0-9a-f]{12}", s))


def bases(split: str, exclude: set):
    out = []
    for f in sorted(glob.glob(str(DATA / "messages" / "*" / f"{split}-*.parquet"))):
        for r in pq.read_table(f, columns=["episode_id", "hidden_spec", "opening", "kind"]).to_pylist():
            if r["kind"] != "baseline" or r["episode_id"] in exclude or not (r["opening"] or "").strip():
                continue
            h = json.loads(r["hidden_spec"])
            b = next((round(p["value"]["amount"] / 100) for p in h["predicates"] if p.get("source") == "stated"
                      and p.get("op") == "max_price" and isinstance(p.get("value"), dict)), None)
            if b is None or b < 5:
                continue
            said = m1.budget_mentions(r["opening"])
            if not any(abs(v - b) <= max(1.0, 0.01 * b) for v in said):     # the opening itself must state it
                continue
            if m1.quantity_mentions(r["opening"]):                           # keep quantity free for P1
                continue
            bundle = any(p.get("op") == "all_of" and isinstance(p.get("value"), list) and len(p["value"]) >= 2
                         for p in h["predicates"])
            out.append((r, b, bundle))
    out.sort(key=lambda x: x[0]["episode_id"])
    seen, uniq = set(), []
    for r, b, bundle in out:    # different journeys can share the same opening text (cause of G1's duplicates)
        k = " ".join(r["opening"].split()).lower()
        if k not in seen:
            seen.add(k)
            uniq.append((r, b, bundle))
    return uniq


def T(role, text, i):
    return {"role": role, "text": text, "turn_id": f"s{i}"}


def make(tp, base, rng, split, n):
    r, B, _bundle = base
    X, Y, Z = int(round(B * 1.3)) + 1, max(1, int(round(B * 0.8))), int(round(B * 1.1))
    names = rng.sample(NAMES, 3)
    d = [T("user", r["opening"], 0)]
    per_turn = [{"budget_max": B}]
    gold = {"budget_max": B}
    expect_no_question = False
    if tp == "N0":
        d += [T("assistant", W["a_continue"], 1), T("user", W["u_neutral1"], 2), T("assistant", W["a_keep"], 3),
              T("user", W["u_neutral2"], 4)]
        per_turn += [{"budget_max": B}, {"budget_max": B}]
        expect_no_question = True
    elif tp == "L1":
        if n % 2 == 0:
            d += [T("assistant", W["a_ack"], 1), T("user", W["u_relax"].replace("{X}", str(X)), 2)]
            gold["budget_max"] = X
        else:
            d += [T("assistant", W["a_ack"], 1), T("user", W["u_tighten"].replace("{Y}", str(Y)), 2)]
            gold["budget_max"] = Y
        per_turn += [{"budget_max": gold["budget_max"]}]
        expect_no_question = True
    elif tp == "L2":
        d += [T("assistant", W["a_ack"], 1), T("user", W["u_tighten"].replace("{Y}", str(Y)), 2),
              T("assistant", W["a_ack_value"].replace("{V}", str(Y)), 3), T("user", W["u_relax"].replace("{X}", str(X)), 4)]
        per_turn += [{"budget_max": Y}, {"budget_max": X}]
        gold["budget_max"] = X
        if n % 2 == 1:
            d += [T("assistant", W["a_ack_value"].replace("{V}", str(X)), 5), T("user", W["u_tighten2"].replace("{Z}", str(Z)), 6)]
            per_turn += [{"budget_max": Z}]
            gold["budget_max"] = Z
        expect_no_question = True
    elif tp == "P1":
        d += [T("assistant", W["a_ack"], 1), T("user", W["u_qty"], 2), T("assistant", W["a_ack_qty"], 3),
              T("user", W["u_relax"].replace("{X}", str(X)), 4)]
        per_turn += [{"budget_max": B, "quantity": 2}, {"budget_max": X, "quantity": 2}]
        gold = {"budget_max": X, "quantity": 2}
        expect_no_question = True
    elif tp in ("S1", "S2"):
        ps = [f"{B * f:.2f}" for f in ((0.6, 0.8, 0.9) if tp == "S1" else (0.7, 1.3, 0.9))]
        lst = W["a_list"].format(N1=names[0], N2=names[1], N3=names[2], P1=ps[0], P2=ps[1], P3=ps[2])
        d += [T("assistant", lst, 1), T("user", W["u_pick2"], 2)]
        per_turn += [{"budget_max": B}]
        expect_no_question = tp == "S1"
    elif tp == "U2":
        d += [T("assistant", W["a_recommend"].format(N1=names[0], P1=f"{B * 1.4:.2f}"), 1), T("user", W["u_looks_nice"], 2)]
        per_turn += [{"budget_max": B}]
    return {"case_id": f"G1v2-{split}-{tp}-{n:02d}", "type": tp, "split": split, "base_episode_id": r["episode_id"],
            "provenance": "generated:G1v2(original wording)", "dialogue": d,
            "gold": {"final": gold, "per_user_turn": per_turn, "expect_no_question": expect_no_question}}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    excl = exposure_ids()
    man = {"seed": SEED, "per_type": PER_TYPE, "types": TYPES, "model_calls": 0,
           "wording_sha256": hashlib.sha256(json.dumps(W, sort_keys=True).encode()).hexdigest(),
           "exposure_excluded": len(excl), "splits": {}}
    used_all = set()
    for name, split in SPLITS.items():
        rng = random.Random(f"{SEED}-{name}")
        pool = bases(split, excl)
        need = PER_TYPE * len(TYPES)
        if len(pool) < need:
            raise SystemExit(f"{split}: only {len(pool)} usable base journeys, need {need}")
        # P1 adds "I need 2 of them": only on non-bundle journeys (with "one of each" the quantity would be ambiguous)
        p1 = rng.sample([b for b in pool if not b[2]], PER_TYPE)
        rest = rng.sample([b for b in pool if b not in p1], need - PER_TYPE)   # without replacement
        assign, j = {}, 0
        for tp in TYPES:
            if tp == "P1":
                assign[tp] = p1
            else:
                assign[tp], j = rest[j:j + PER_TYPE], j + PER_TYPE
        cases = [make(tp, assign[tp][k], rng, name, k) for tp in TYPES for k in range(PER_TYPE)]
        keys = Counter(tuple(t["text"] for t in c["dialogue"]) for c in cases)
        dup = [k for k, v in keys.items() if v > 1]
        if dup:
            raise SystemExit(f"{split}: {len(dup)} duplicate dialogues")
        ids = {c["base_episode_id"] for c in cases}
        assert not (ids & used_all), "base journey reused across splits"
        used_all |= ids
        path = OUT / f"{name}.jsonl"
        path.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases), encoding="utf-8", newline="\n")
        man["splits"][name] = {"source_split": split, "usable_bases": len(pool), "cases": len(cases),
                               "by_type": dict(Counter(c["type"] for c in cases)),
                               "user_turns": sum(1 for c in cases for t in c["dialogue"] if t["role"] == "user"),
                               "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                               "case_ids_sha256": hashlib.sha256("\n".join(c["case_id"] for c in cases).encode()).hexdigest(),
                               "base_episode_ids": sorted(ids)}
    man["generator_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in man.items() if k != "splits"} |
                     {"splits": {k: {x: y for x, y in v.items() if x != "base_episode_ids"} for k, v in man["splits"].items()}}, indent=1))


if __name__ == "__main__":
    main()
