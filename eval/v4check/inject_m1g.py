"""v4 dev intervention path: M1 v1 vs M1 v2 vs M1-G on the same candidate operations (labels = operation_labels).

M1-G calls gpt-6-luna (reasoning low) once per candidate whose cited turn is a user turn; it is run TWICE with
separate ledgers (no replay cache between runs) to report run-to-run agreement. v1/v2 are model-free (NLI for v2).
Prior ledger: v4 initial_state (oracle prior of the intervention design). Dev only; eval after the main M1 is fixed.
Output: results/m1g_20261126/{inject_dev.json, INJECT_DEV.md, rows_dev.jsonl, ledger_run1.jsonl, ledger_run2.jsonl}
Usage: dry  .venv/Scripts/python.exe eval/v4check/inject_m1g.py --dry-run
       live .venv/Scripts/python.exe eval/v4check/inject_m1g.py --budget 0.15   (after plan approval)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/v3check", "eval/e_m1"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import inject as I  # noqa: E402
import run as R  # noqa: E402  (DryLLM)
from cdv.extract import OpenAIResponses  # noqa: E402
from cdv.m1 import UserTurn  # noqa: E402
from cdv.v2 import m1g  # noqa: E402

V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4")
OUT = ROOT / "results" / "m1g_20261126"
D = ("ACCEPT", "REJECT", "CLARIFY", "UNSUPPORTED")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default="gpt-6-luna")
    ap.add_argument("--budget", type=float, default=0.15, help="cap per run (each run has its own ledger)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--prompt-version", default="v1", choices=["v1", "v2"])
    # harness options added 2026-11-27 after the policy freeze (defaults = the dev runs above, unchanged)
    ap.add_argument("--data", type=Path, default=V4)
    ap.add_argument("--name", default="v4")
    ap.add_argument("--split", default="dev")
    a = ap.parse_args()
    global OUT
    if a.prompt_version != "v1":                    # v1 outputs are never overwritten
        OUT = OUT / f"prompt_{a.prompt_version}"
    if (a.name, a.split) != ("v4", "dev"):          # other data: own sub-folder (file names kept)
        OUT = OUT / f"{a.name}_{a.split}"
    eps = {json.loads(l)["episode_id"]: json.loads(l) for l in (a.data / a.split / "episodes.jsonl").read_text(encoding="utf-8").splitlines() if l}
    gold = {json.loads(l)["episode_id"]: json.loads(l) for l in (a.data / a.split / "episode_gold.jsonl").read_text(encoding="utf-8").splitlines() if l}
    items = []
    for e, ep in eps.items():
        g = gold[e]
        cat = {c["sku"]: c for c in ep["catalog"]}
        turns = [dict(x, idx=i) for i, x in enumerate(ep["dialogue"])]
        by = {x["turn_id"]: x for x in turns}
        for op in ep["candidate_operations"]:
            t = by.get(op["evidence_turn_id"]) or {}
            items.append({"episode_id": e, "group": g["group"], "subtype": g["subtype"], "op": op, "cat": cat, "turns": turns,
                          "role": t.get("role"), "text": t.get("text"), "label": g["operation_labels"][op["op_id"]].upper(),
                          "prior": g["initial_state"]})
    n_calls = sum(1 for it in items if it["role"] == "user")
    OUT.mkdir(parents=True, exist_ok=True)
    if a.dry_run:
        dl = R.DryLLM()
        for it in items:
            if it["role"] == "user":
                dl(m1g.SYSTEM, m1g.TEMPLATES[a.prompt_version].format(turn=it["text"], change=m1g.describe(it["op"], it["cat"])))
        out = {"ops": len(items), "calls_per_run": n_calls, "runs": 2, "input_tokens_est_per_run": int(dl.chars_in / 4),
               "prompt_version": a.prompt_version,
               "prompt_sha256": m1g.PROMPT_SHA256 if a.prompt_version == "v1" else m1g.PROMPT_V2_SHA256}
        (OUT / "dry_run.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps(out))
        return
    for f in ("rows_dev.jsonl", "ledger_run1.jsonl", "ledger_run2.jsonl"):
        assert not (OUT / f).exists(), f"refusing to overwrite {f}"
    runs = {}
    for k in (1, 2):
        llm = OpenAIResponses(a.model, OUT / f"ledger_run{k}.jsonl", a.budget)

        def job(it, llm=llm):
            return m1g.decide_v(llm, it["op"], it["role"], it["text"], it["cat"], a.prompt_version)
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            runs[k] = list(ex.map(job, items))
    from cdv.nli import NLI
    nli = NLI()
    rows, cm = [], defaultdict(lambda: defaultdict(Counter))
    for it, r1, r2 in zip(items, runs[1], runs[2]):
        users = {x["turn_id"]: UserTurn(x["turn_id"], x["idx"], x["text"]) for x in it["turns"] if x["role"] == "user"}
        prev = I.prior_ledger(it["prior"], it["cat"])
        d1 = I.v1_decide(prev, it["op"], it["cat"], it["turns"], users)
        d2 = I.v2_decide(prev, it["op"], it["cat"], it["turns"], users, nli)
        row = {"episode_id": it["episode_id"], "group": it["group"], "subtype": it["subtype"], "op": it["op"]["operation"],
               "field": it["op"]["field"], "cited_role": it["role"], "label": it["label"], "v1": d1, "v2": d2,
               "m1g_run1": r1[0], "m1g_label_run1": r1[1], "m1g_run2": r2[0], "m1g_label_run2": r2[1]}
        rows.append(row)
        for arm in ("v1", "v2", "m1g_run1", "m1g_run2"):
            cm[arm][f"ALL|{it['label']}"][row[arm]] += 1
            cm[arm][f"{it['group']}/{it['subtype']}|{it['label']}"][row[arm]] += 1
    called = [r for r in rows if r["cited_role"] == "user"]
    agree_dec = sum(r["m1g_run1"] == r["m1g_run2"] for r in called)
    agree_lab = sum(r["m1g_label_run1"] == r["m1g_label_run2"] for r in called)
    cost = {k: round(sum(x[2] for x in runs[k]), 6) for k in (1, 2)}
    psha = m1g.PROMPT_SHA256 if a.prompt_version == "v1" else m1g.PROMPT_V2_SHA256
    res = {"ops": len(rows), "calls_per_run": len(called), "cost_usd": cost, "prompt_version": a.prompt_version, "prompt_sha256": psha,
           "run_agreement": {"decision": f"{agree_dec}/{len(called)}", "label": f"{agree_lab}/{len(called)}"},
           "unparsed": {k: sum(1 for x in runs[k] if x[1] == "unparsed") for k in (1, 2)},
           "confusion": {arm: {k: dict(v) for k, v in sorted(m.items())} for arm, m in cm.items()}}
    (OUT / "inject_dev.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
    (OUT / "rows_dev.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="\n")
    md = ["# v4 dev 주입: M1 v1 대 v2 대 M1-G (정답 operation_labels)", "",
          f"- 후보 {len(rows)}개, M1-G 호출 실행당 {len(called)}회 × 2회, 비용 {cost}. 프롬프트 {a.prompt_version} sha256 `{psha}`.",
          f"- M1-G 두 실행의 일치: 판정 {agree_dec}/{len(called)}, 분류 {agree_lab}/{len(called)}. 해석 실패 {res['unparsed']}.", "",
          "| 정답 | n | v1 수용/거부/확인/미지원 | v2 | M1-G 1회 | M1-G 2회 |", "|---|---:|---|---|---|---|"]
    for lab in ("ACCEPT", "CLARIFY", "REJECT"):
        k = f"ALL|{lab}"
        n = sum(cm["v1"][k].values())
        md.append(f"| {lab} | {n} | " + " | ".join(" / ".join(str(cm[arm][k].get(d, 0)) for d in D)
                                                 for arm in ("v1", "v2", "m1g_run1", "m1g_run2")) + " |")
    (OUT / "INJECT_DEV.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
