"""v3 intervention path: inject candidate_operations into M1 v1 and M1 v2 and compare with the dataset's labels.

No model calls. v3 files are read as data (none of its code is run). This is the 'change-candidate intervention'
path of v3: pass rates here are NOT extractor error rates (v3 README).
Labels per candidate operation (v3 has no 'operation_labels' field): ACCEPT if it is in episode_gold.accepted_changes,
REJECT if in proposed_invalid_operations (matched on operation, field, evidence turn).
Prior ledger: episode_gold.initial_state (an oracle prior, as in v3's intervention design) mapped to the M1 schema.
Mapping v3 -> M1 fields: Price -> budget_max (/100), Quantity -> quantity (sum), Brand -> brand_in / brand_out,
  Bundle -> bundle_all (catalog titles), Fulfillment delivery|pickup -> ship|pickup, Deadline -> deadline_days,
  Substitution -> substitute (named alternative brand), Product -> v1: product_type (title); v2: selection S,
  Attribute -> no field in M1 v1/v2: reported as UNSUPPORTED (not applied).
Decisions: ACCEPT (applied) / REJECT (not applied) / CLARIFY (held for the user) / UNSUPPORTED.
  v1 = cdv.m1.verify_turn on the op with its cited turn (PLAN_v3 rules, unchanged).
  v2 = M1 v2 rules: the cited turn must state the value (rule anchor with quantity context, then NLI); otherwise
       NON_USER_SOURCE (value in agent/tool text) -> REJECT or NOT_FOUND -> CLARIFY; Product ops go to selection:
       a user's pick within the constraints is applied, outside them needs an explicit cue (else CLARIFY).
Output: results/v3check_20261126/inject_{split}.json, INJECT_{split}.md
Usage: .venv/Scripts/python.exe eval/v3check/inject.py --split dev
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cdv import m1  # noqa: E402
from cdv.m1 import ChangeOp, Entry, Ledger, UserTurn  # noqa: E402
from cdv.v2.candidates import overlap, toks  # noqa: E402
from cdv.v2.m1v2 import anchor_v2, in_non_user_text  # noqa: E402

V3 = Path(r"C:/Users/user/Documents/Codex/2026-11-26/c-ct/outputs/carttrace_eval_v3")
OUT = ROOT / "results" / "v3check_20261126"
OPMAP = {"RELAX": "relax", "TIGHTEN": "tighten", "OVERRIDE": "override", "ADD": "add", "REVOKE": "revoke",
         "SUBSTITUTE": "add_substitute"}


def entries_from(field, value, cat, basis=()):
    """v3 field/value -> list of (entry_id, Entry|None). None = remove."""
    if field == "Price":
        return [("budget", None if value is None else Entry("budget", "budget_max", value / 100, basis=basis))]
    if field == "Quantity":
        return [("qty", None if not value else Entry("qty", "quantity", int(sum(value.values())), basis=basis))]
    if field == "Brand":
        v = value or {}
        return [("brand_in", Entry("brand_in", "brand_in", tuple(v["include"]), basis=basis) if v.get("include") else None),
                ("brand_out", Entry("brand_out", "brand_out", tuple(v["exclude"]), basis=basis) if v.get("exclude") else None)]
    if field == "Bundle":
        return [("bundle", Entry("bundle", "bundle_all", tuple(cat.get(s, {}).get("title", s) for s in value), basis=basis)
                 if value and len(value) >= 2 else None)]
    if field == "Fulfillment":
        return [("ful", None if not value else Entry("ful", "fulfillment", "ship" if value == "delivery" else value, basis=basis))]
    if field == "Deadline":
        return [("deadline", None if value is None else Entry("deadline", "deadline_days", int(value), basis=basis))]
    if field == "Substitution":
        if not value:
            return [("sub", None)]
        alts = sorted({cat.get(a, {}).get("brand") or "" for a in value.values()} - {""})
        return [("sub", Entry("sub", "substitute", None, basis=basis,
                              scope={"named": bool(alts), "then": {"budget_max": None, "product_type": None,
                                                                   "brand_in": alts or None}}))]
    if field == "Product":
        return [("ptype", Entry("ptype", "product_type", " / ".join(cat.get(s, {}).get("title", s) for s in value),
                                strength="soft", basis=basis) if value else None)]
    return []   # Attribute: unsupported


def prior_ledger(init, cat):
    es = {}
    for f in ("Price", "Quantity", "Brand", "Bundle", "Fulfillment", "Deadline", "Substitution", "Product"):
        if f in init:
            for eid, e in entries_from(f, init[f], cat, basis=("u00",)):
                if e is not None:
                    es[eid] = e
    return Ledger(1, tuple(es.values()))


def v1_decide(prev: Ledger, op, cat, turns, users):
    if op["field"] == "Attribute":
        return "UNSUPPORTED"
    t = op["evidence_turn_id"]
    cited = (t,) if t in users else (t,)          # cited as given; a non-user turn fails check_source
    ops = []
    for eid, e in entries_from(op["field"], op["value"], cat, basis=cited):
        p = prev.by_id().get(eid)
        if e is None and p is None:
            continue
        o = OPMAP[op["operation"]] if not (e is None) else "revoke"
        if op["field"] == "Brand" and p is None and e is not None:
            o = "add"
        ops.append(ChangeOp(o, eid, e, cited))
    if not ops:
        return "ACCEPT"
    res = m1.verify_turn(prev, ops, list(users.values()))
    st = {f.status for f in res.change_findings}
    return "REJECT" if m1.REJECT in st else ("CLARIFY" if m1.PENDING in st else "ACCEPT")


def v2_decide(prev: Ledger, op, cat, turns, users, nli):
    if op["field"] == "Attribute":
        return "UNSUPPORTED"
    t = op["evidence_turn_id"]
    if t not in users:
        return "REJECT"                                   # not a user turn: NON_USER_SOURCE
    text = users[t].text
    before = [x["text"] for x in turns if x["role"] != "user" and x["idx"] < users[t].seq]
    if op["field"] == "Product":                          # selection S
        picked = [cat[s] for s in op["value"] if s in cat]
        named = [p for p in picked if overlap(p["title"], text) >= 0.5 or (p.get("brand") and p["brand"].lower() in text.lower())]
        if not named:
            return "CLARIFY"                              # NOT_FOUND: the user did not pick it in that turn
        by = prev.by_id()
        ok = True
        if "brand_in" in by and not all(any(b.lower() in (p.get("brand") or p["title"]).lower() for b in by["brand_in"].value) for p in named):
            ok = False
        if "brand_out" in by and any(b.lower() in (p.get("brand") or p["title"]).lower() for b in by["brand_out"].value for p in named):
            ok = False
        if "budget" in by and sum(p.get("unit_minor", 0) for p in named) / 100 > float(by["budget"].value) + 1e-6:
            ok = False
        if ok:
            return "ACCEPT"
        return "ACCEPT" if m1.WIDEN_CUES.search(text) else "CLARIFY"
    decisions = []
    for eid, e in entries_from(op["field"], op["value"], cat, basis=(t,)):
        p = prev.by_id().get(eid)
        if e is None and p is None:
            continue
        o = "revoke" if e is None else (OPMAP[op["operation"]] if p is not None or op["operation"] != "OVERRIDE" else "add")
        cited, how = anchor_v2(e, o, [users[t]], nli)
        if not cited:
            decisions.append("REJECT" if (e is not None and in_non_user_text(e, before)) else
                             ("REJECT" if o == "revoke" else "CLARIFY"))
            continue
        res = m1.verify_turn(prev, [ChangeOp(o, eid, e if e is None else Entry(e.id, e.field, e.value, e.strength, cited, e.scope), cited)],
                             list(users.values()))
        f = res.change_findings[0].status
        decisions.append("REJECT" if f == m1.REJECT else ("CLARIFY" if f == m1.PENDING else "ACCEPT"))
    if not decisions:
        return "ACCEPT"
    return "REJECT" if "REJECT" in decisions else ("CLARIFY" if "CLARIFY" in decisions else "ACCEPT")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "eval"], default="dev")
    ap.add_argument("--no-nli", action="store_true")
    ap.add_argument("--tag", default="", help="output suffix; existing outputs are never overwritten")
    a = ap.parse_args()
    sfx = f"_{a.tag}" if a.tag else ""
    for f in (f"inject_{a.split}{sfx}.json", f"inject_rows_{a.split}{sfx}.jsonl", f"INJECT_{a.split}{sfx}.md"):
        assert not (OUT / f).exists(), f"refusing to overwrite {f}"
    eps = {json.loads(l)["episode_id"]: json.loads(l) for l in (V3 / a.split / "episodes.jsonl").read_text(encoding="utf-8").splitlines() if l}
    gold = {json.loads(l)["episode_id"]: json.loads(l) for l in (V3 / a.split / "episode_gold.jsonl").read_text(encoding="utf-8").splitlines() if l}
    nli = None
    if not a.no_nli:
        from cdv.nli import NLI
        nli = NLI()
    rows = []
    for e, ep in eps.items():
        g = gold[e]
        ops = ep["candidate_operations"]
        if not ops:
            continue
        cat = {c["sku"]: c for c in ep["catalog"]}
        turns = [dict(x, idx=i) for i, x in enumerate(ep["dialogue"])]
        users = {x["turn_id"]: UserTurn(x["turn_id"], x["idx"], x["text"]) for x in turns if x["role"] == "user"}
        acc = {(o["operation"], o["field"], o["evidence_turn_id"]) for o in g["accepted_changes"]}
        inv = {(o["operation"], o["field"], o["evidence_turn_id"]) for o in g["proposed_invalid_operations"]}
        prev1 = prev2 = prior_ledger(g["initial_state"], cat)
        for op in sorted(ops, key=lambda o: next((x["idx"] for x in turns if x["turn_id"] == o["evidence_turn_id"]), 0)):
            k = (op["operation"], op["field"], op["evidence_turn_id"])
            label = "ACCEPT" if k in acc else ("REJECT" if k in inv else "UNLABELED")
            if g["subtype"] == "induced_consent":
                label = "CLARIFY"          # researcher correction 2026-11-26: consent on a disputed premise -> ask
            d1 = v1_decide(prev1, op, cat, turns, users)
            d2 = v2_decide(prev2, op, cat, turns, users, nli)
            rows.append({"episode_id": e, "group": g["group"], "subtype": g["subtype"], "op": op["operation"],
                         "field": op["field"], "evidence_role": next((x["role"] for x in turns if x["turn_id"] == op["evidence_turn_id"]), None),
                         "label": label, "v1": d1, "v2": d2})
    cm = {v: defaultdict(Counter) for v in ("v1", "v2")}
    for r in rows:
        for v in ("v1", "v2"):
            cm[v][f"{r['group']}/{r['subtype']}|{r['label']}"][r[v]] += 1
            cm[v][f"ALL|{r['label']}"][r[v]] += 1
    res = {"note": __doc__.split("\n\n")[0], "split": a.split, "n_ops": len(rows),
           "labels": dict(Counter(r["label"] for r in rows)),
           "confusion": {v: {k: dict(c) for k, c in sorted(m.items())} for v, m in cm.items()}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"inject_{a.split}{sfx}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (OUT / f"inject_rows_{a.split}{sfx}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="\n")
    D = ("ACCEPT", "REJECT", "CLARIFY", "UNSUPPORTED")
    md = [f"# v3 변경 후보 개입 경로 ({a.split}): M1 v1 대 v2 혼동 행렬", "",
          "- 이 경로의 통과율은 추출기 오류율이 아니다(v3 README). 이전 장부는 v3 정답 initial_state(오라클). 표지는 accepted_changes = 수용, proposed_invalid_operations = 거부.",
          "- 생성 데이터(v3: CartTrace 카탈로그 + 합성 대화). 주 결과와 분리해 보고한다.", "",
          "| 유형 | 정답 | n | v1 수용/거부/확인/미지원 | v2 수용/거부/확인/미지원 |", "|---|---|---:|---|---|"]
    keys = sorted({k for m in cm.values() for k in m}, key=lambda k: (k.startswith("ALL"), k))
    for k in keys:
        grp, lab = k.split("|")
        n = sum(cm["v1"][k].values())
        md.append(f"| {grp} | {lab} | {n} | " + " / ".join(str(cm["v1"][k].get(d, 0)) for d in D) + " | " +
                  " / ".join(str(cm["v2"][k].get(d, 0)) for d in D) + " |")
    (OUT / f"INJECT_{a.split}{sfx}.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
