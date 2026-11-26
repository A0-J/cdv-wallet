"""Sealed-sample final evaluation: S_R1 300 (test_cross_template) + S_R3 100 (train), ID list sha256 540669d1...

Run ONLY after the researcher approves results/frozen_610a97c/PLAN_EVAL_SEALED.md (plan sha reported to them).
Every decision path is the policy-freeze commit 610a97c (cdv/, eval/integrated/, eval/e_m1/, eval/m1_v2/); the
script refuses to start if those folders differ from 610a97c. This file only does input/output:
  extract  FnCTOD + plain LLM on the shopper/agent messages before the decision point t
           (same selection of messages, decision point and extractor as P2 eval/integrated/extract_dev.py)
  eval     eval/integrated/dev_eval.py main() with its data folder pointed at this run's folder
           (main M1 = M1-G prompt v2, arms B0-B4, B3_v2, v1, AV0-AV2, U reference; unverified policy consent_clarify)
  precheck PRECHECK baseline (cdv/v2/baselines.py, prompts sha d9c696fe..., unchanged) through a CartTrace adaptor:
           the shopper/agent messages before the same decision point t that the gate arms use (eval/integrated/env.py
           build_case), and the payment request = the charged cart lines (title, structured brand, unit price,
           quantity), fees = payment total - line sum, fulfillment / days only at a consent-request point (as the gate).
           --sample validation runs the same adaptor on the 306 P2 validation journeys (development pilot)
  agree    run 1 vs run 2 (no model calls): per-arm decision agreement (incl. PRECHECK), final extracted state
           agreement, and the main groups of each run side by side
Each run has its own folder and ledgers, so run 2 never replays run 1's answers (the replay cache is per ledger).
Dry run: counts only. No dialogue text is printed or written by any step.
Output: results/sealed_eval_610a97c/run{1,2}/{extract_S_R1.jsonl, extract_S_R3.jsonl, extract_summary.json, ledger.jsonl,
        dev_rows_run{k}.jsonl, dev_summary_run{k}.json, ledger_m1g_run{k}.jsonl}, results/sealed_eval_610a97c/AGREEMENT.md
Usage:
  dry   .venv/Scripts/python.exe eval/seal/run_sealed.py --run 1 --step extract --dry-run
  live  .venv/Scripts/python.exe eval/seal/run_sealed.py --run 1 --step extract --budget 0.40
        .venv/Scripts/python.exe eval/seal/run_sealed.py --run 1 --step eval --m1g-budget 0.15
        .venv/Scripts/python.exe eval/seal/run_sealed.py --run 1 --step precheck --precheck-budget 0.075
        (the same three for --run 2), then  .venv/Scripts/python.exe eval/seal/run_sealed.py --step agree
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/integrated", "eval/e_m1", "eval/m1_v2", "eval/seal"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

SEAL = ROOT / "results" / "sealed_20261126"
OUT = ROOT / "results" / "sealed_eval_610a97c"
FREEZE = "610a97c"
FROZEN_PATHS = ("cdv", "eval/integrated", "eval/e_m1", "eval/m1_v2")
IDS_FILE_SHA = "2d42c0cb20eddebdbf9a854eee3dc25e7f6885bdde984bd935d84f7fdd3597a9"
IDS_LIST_SHA = "540669d10c44bb26a9dfe208a01268d1ade649ea3375ba9eff32ce8a449bfb46"
SETS = {"S_R1": "test_cross_template", "S_R3": "train"}


ALLOW_NEW = {"eval/integrated/paired_compare.py"}   # analysis-only file; not imported by any decision code


def check_frozen(base: Path | None = None):
    """Allow-list freeze check (runner change, researcher decision 2026-11-27).
    Every file the freeze commit has under FROZEN_PATHS must exist and be byte-identical in git's stored form
    (git hash-object with the path's filters, as core.autocrlf=true here) to the freeze-commit blob; a file not in the
    freeze commit is allowed only if listed in ALLOW_NEW. Any other addition, deletion or change -> refuse.
    __pycache__ folders (untracked bytecode caches) are ignored. `base` = folder to check (default: this repo)."""
    base = Path(base) if base else ROOT
    ls = subprocess.run(["git", "ls-tree", "-r", FREEZE, "--", *FROZEN_PATHS], cwd=ROOT, capture_output=True, text=True, check=True)
    frozen = {l.split("\t", 1)[1]: l.split()[2] for l in ls.stdout.splitlines() if "\t" in l}
    now = {p.relative_to(base).as_posix() for fp in FROZEN_PATHS for p in (base / fp).rglob("*")
           if p.is_file() and "__pycache__" not in p.parts}
    problems = []
    for rel, sha in sorted(frozen.items()):
        f = base / rel
        if not f.exists():
            problems.append(f"deleted: {rel}")
            continue
        h = subprocess.run(["git", "hash-object", "--path", rel, str(f)], cwd=ROOT, capture_output=True, text=True, check=True)
        if h.stdout.strip() != sha:
            problems.append(f"changed: {rel}")
    problems += [f"added (not allow-listed): {rel}" for rel in sorted(now - set(frozen)) if rel not in ALLOW_NEW]
    if problems:
        raise SystemExit(f"decision code differs from the freeze commit {FREEZE}: {problems[:10]}; nothing was run")
    return True


def sealed_ids() -> dict:
    raw = (SEAL / "sealed_ids.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != IDS_FILE_SHA:
        raise SystemExit("sealed_ids.json sha256 differs from SEALED.md; nothing was run")
    d = json.loads(raw.decode("utf-8"))
    # same formula as draw_sealed.py: S_R1 sorted, then S_R3 sorted, newline-joined
    if hashlib.sha256("\n".join(sorted(d["S_R1"]) + sorted(d["S_R3"])).encode("utf-8")).hexdigest() != IDS_LIST_SHA:
        raise SystemExit("sealed ID list sha256 differs from SEALED.md; nothing was run")
    return {"S_R1": d["S_R1"], "S_R3": d["S_R3"]}


def step_extract(a, rd: Path):
    import diagnose as D
    import run as R
    from cdv.extract import OpenAIResponses
    from recompute_truncated import decision_point
    ids = sealed_ids()
    rd.mkdir(parents=True, exist_ok=True)
    sfx = "_dry" if a.dry_run else ""
    for s in SETS:
        assert a.dry_run or not (rd / f"extract_{s}.jsonl").exists(), f"refusing to overwrite extract_{s}.jsonl"
    llm = R.DryLLM() if a.dry_run else OpenAIResponses(a.model, rd / "ledger.jsonl", a.budget)
    summ = {"run": a.run, "freeze_commit": FREEZE, "ids_sha256": IDS_LIST_SHA, "dry_run": a.dry_run,
            "model": None if a.dry_run else a.model, "sets": {}}
    for s, split in SETS.items():
        want = set(ids[s])
        meta = {r["episode_id"]: r for r in R.load_messages([split]) if r["episode_id"] in want}
        T = D.load_turns(want, splits=(split,))
        items, excluded = [], []
        for e in sorted(want):
            if e not in meta or e not in T:
                excluded.append({"episode_id": e, "reason": "not found in split"})
                continue
            t, kind = decision_point(T[e])
            dlg = [x for x in T[e] if x["kind"] == "message" and x["actor"] in ("shopper", "agent")
                   and (x["text"] or "").strip() and x["seq"] < t]
            if not any(x["actor"] == "shopper" for x in dlg):
                excluded.append({"episode_id": e, "reason": "no shopper turn before t"})
                continue
            items.append((meta[e], t, kind, dlg))
        ext = R.parallel_extract([(r["episode_id"], dlg) for r, t, kind, dlg in items], llm, llm, a.workers)
        out, failed = [], []
        for r, t, kind, dlg in items:
            v = ext[r["episode_id"]]
            if isinstance(v, Exception):
                failed.append({"episode_id": r["episode_id"], "error": type(v).__name__})
                continue
            fn, pl, t_fn = v
            out.append({"episode_id": r["episode_id"], "set": s, "outcome": r["outcome_class"], "t": t, "t_kind": kind,
                        "n_user_turns_before_t": sum(1 for x in dlg if x["actor"] == "shopper"),
                        "fnctod_states": [{"turn_id": x["turn_id"], "selected": x.get("selected"), "state": x["state"]} for x in fn],
                        "plain_state": pl["state"], "cost_usd": round(sum(x["cost_usd"] for x in fn) + pl["cost_usd"], 6),
                        "extract_s": round(t_fn, 3)})
        if not a.dry_run:
            (rd / f"extract_{s}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out),
                                                   encoding="utf-8", newline="\n")
        summ["sets"][s] = {"split": split, "n_ids": len(want), "n_done": len(out), "excluded": excluded, "failed": failed,
                           "outcomes": dict(Counter(x["outcome"] for x in out)),
                           "t_kind": dict(Counter(x["t_kind"] for x in out)),
                           "user_turns_before_t": sum(x["n_user_turns_before_t"] for x in out)}
    if a.dry_run:
        summ["dry_run_estimate"] = {"calls_lower_bound": llm.calls, "input_tokens_est": int(llm.chars_in / 4)}
    else:
        summ["cost_usd"], summ["cache_hits"] = round(llm.spent, 6), llm.cache_hits
    (rd / f"extract_summary{sfx}.json").write_text(json.dumps(summ, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in summ.items() if k != "sets"} |
                     {"sets": {s: {k: v for k, v in d.items() if k not in ("excluded", "failed")} | {"excluded": len(d["excluded"]), "failed": len(d["failed"])}
                               for s, d in summ["sets"].items()}}))


def step_eval(a, rd: Path):
    import dev_eval as DE
    for s in SETS:
        if not (rd / f"extract_{s}.jsonl").exists():
            raise SystemExit(f"run the extract step for run {a.run} first ({s} missing)")
    DE.DEV, DE.SETS = rd, tuple(SETS)
    sys.argv = ["dev_eval.py", "--m1g", "--tag", f"run{a.run}", "--m1g-budget", str(a.m1g_budget)]
    DE.main()


def _in_group(r, g) -> bool:
    return {"legit(outcome)": r["outcome"] in ("RIGHT", "RIGHT_BY_LUCK"), "pay_viol(U denies)": r["pay_viol"],
            "violating_not_pay_checkable": r["outcome"] in ("WRONG", "WRONG_HIDDEN") and not r["pay_viol"]}[g]


def precheck_items(sample: str):
    """(episode_id, set, outcome, turns, lines, kw) for the PRECHECK adaptor; same case builder as the gate arms."""
    import env as E
    if sample == "sealed":
        ids = sealed_ids()
        sets = {e: s for s in SETS for e in ids[s]}
    else:
        d = ROOT / "results" / "integrated_dev_20261126"
        sets = {json.loads(l)["episode_id"]: s for s in ("V1", "V3", "V2")
                for l in (d / f"extract_{s}.jsonl").read_text(encoding="utf-8").splitlines() if l}
    cases = E.build_cases(set(sets))
    out = []
    for e in sorted(sets):
        c = cases[e]
        turns = [x[1:] for x in sorted([(u.seq, "shopper", u.text) for u in c.user_turns]
                                       + [(q, "agent", t) for q, t in c.agent_turns])]
        lines = []
        for key, qty in c.cart:
            ln = c.catalog.get(key)
            lines.append({"title": (ln.title if ln else "") or key[1], "brand": ln.brand if (ln and ln.brand_known) else None,
                          "unit_price": ln.unit_price if ln else 0.0, "quantity": qty})
        pt = c.checkout_facts.get("payment_total")
        fees = round(pt - sum(l["unit_price"] * l["quantity"] for l in lines), 2) if isinstance(pt, (int, float)) else None
        kw = {"fees": fees if (fees is not None and fees > 0.004) else None,
              "fulfillment": c.checkout_facts.get("fulfillment"), "days": c.checkout_facts.get("max_days")}
        out.append((e, sets[e], c.scoring["outcome"], turns, lines, kw))
    return out


def step_precheck(a, rd: Path):
    import run as R
    from concurrent.futures import ThreadPoolExecutor
    from cdv.extract import OpenAIResponses
    from cdv.v2 import baselines as Bl
    rd.mkdir(parents=True, exist_ok=True)
    f = rd / (f"precheck_run{a.run}" + ("_dry" if a.dry_run else "") + ".jsonl")
    assert a.dry_run or not f.exists(), f"refusing to overwrite {f.name}"
    items = precheck_items(a.sample)
    llm = R.DryLLM() if a.dry_run else OpenAIResponses(a.model, rd / f"ledger_precheck_run{a.run}.jsonl", a.precheck_budget)

    def job(it):
        e, s, o, turns, lines, kw = it
        try:
            return Bl.precheck(llm, turns, lines, **kw)
        except SystemExit:
            raise
        except Exception as ex:  # noqa: BLE001
            return ("ERROR", True, 0.0, type(ex).__name__)
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        res = list(ex.map(job, items))
    rows = [{"episode_id": e, "set": s, "outcome": o, "precheck": r[0], "unparsed": r[1], "n_turns": len(turns),
             "fees_shown": kw["fees"] is not None, "fulfillment_shown": bool(kw["fulfillment"]),
             "days_shown": kw["days"] is not None}
            for (e, s, o, turns, lines, kw), r in zip(items, res)]
    f.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8", newline="\n")
    summ = {"sample": a.sample, "run": a.run, "n": len(rows), "prompts_sha256": Bl.PROMPTS_SHA256, "dry_run": a.dry_run,
            "decisions": dict(Counter(x["precheck"] for x in rows)), "unparsed": sum(x["unparsed"] for x in rows)}
    if a.dry_run:
        summ["dry_run_estimate"] = {"calls": llm.calls, "input_tokens_est": int(llm.chars_in / 4)}
    else:
        summ["cost_usd"], summ["cache_hits"] = round(llm.spent, 6), llm.cache_hits
    (rd / (f"precheck_summary_run{a.run}" + ("_dry" if a.dry_run else "") + ".json")).write_text(
        json.dumps(summ, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summ))


def step_agree():
    rows, summ = {}, {}
    for k in (1, 2):
        rd = OUT / f"run{k}"
        rows[k] = {json.loads(l)["episode_id"]: json.loads(l) for l in (rd / f"dev_rows_run{k}.jsonl").read_text(encoding="utf-8").splitlines() if l}
        summ[k] = json.loads((rd / f"dev_summary_run{k}.json").read_text(encoding="utf-8"))
        ext = {}
        for s in SETS:
            for l in (rd / f"extract_{s}.jsonl").read_text(encoding="utf-8").splitlines():
                if l:
                    x = json.loads(l)
                    ext[x["episode_id"]] = x["fnctod_states"][-1]["state"] if x["fnctod_states"] else {}
        pf = rd / f"precheck_run{k}.jsonl"
        if pf.exists():
            for l in pf.read_text(encoding="utf-8").splitlines():
                if l:
                    x = json.loads(l)
                    if x["episode_id"] in rows[k]:
                        rows[k][x["episode_id"]]["arms"]["PRECHECK"] = {"decision": x["precheck"]}
        rows[k]["__ext__"] = ext
    ext1, ext2 = rows[1].pop("__ext__"), rows[2].pop("__ext__")
    both = sorted(set(rows[1]) & set(rows[2]))
    arms = [x for x in rows[1][both[0]]["arms"] if x in rows[2][both[0]]["arms"]] if both else []
    res = {"journeys_both_runs": len(both), "final_extracted_state_equal": sum(ext1.get(e) == ext2.get(e) for e in both),
           "decision_agreement": {}}
    for arm in arms:
        same = sum(rows[1][e]["arms"][arm]["decision"] == rows[2][e]["arms"][arm]["decision"] for e in both)
        res["decision_agreement"][arm] = f"{same}/{len(both)}"
    md = ["# 봉인 표본 최종 평가: 1회 대 2회 (고정 커밋 610a97c, 모델 호출 0)", "",
          f"- 두 회차에 모두 있는 여정 {len(both)}. 마지막 추출 상태가 같은 여정 {res['final_extracted_state_equal']}.", "",
          "| 비교군 | 판정 일치 |", "|---|---:|"] + [f"| {a} | {v} |" for a, v in res["decision_agreement"].items()]
    md += ["", "## 회차별 주요 집단 (dev_eval 요약 그대로)", ""]
    for g in ("legit(outcome)", "pay_viol(U denies)", "violating_not_pay_checkable"):
        md += [f"### {g}", "", "| 비교군 | 1회 A/C/D | 2회 A/C/D |", "|---|---|---|"]
        for arm in arms:
            cells = []
            for k in (1, 2):
                x = summ[k]["groups"].get(g, {}).get(arm)
                if x is None and arm == "PRECHECK":           # not in dev_eval's summary: count from the joined rows
                    G = [r for r in rows[k].values() if _in_group(r, g) and "PRECHECK" in r["arms"]]
                    c = Counter(r["arms"]["PRECHECK"]["decision"] for r in G)
                    x = {"ALLOW": c["ALLOW"], "CLARIFY": c["CLARIFY"], "DENY": c["DENY"]} if G else None
                cells.append(f"{x['ALLOW']}/{x['CLARIFY']}/{x['DENY']} (n={summ[k]['groups'][g]['n']})" if x else "-")
            md.append(f"| {arm} | {cells[0]} | {cells[1]} |")
        md.append("")
    md += ["## McNemar (회차별, dev_eval 요약 그대로)", ""]
    for k in (1, 2):
        md.append(f"- {k}회 정상 차단: {json.dumps(summ[k]['mcnemar_legit_blocked'], ensure_ascii=False)}")
        md.append(f"- {k}회 결제 확인 가능 위반 차단: {json.dumps(summ[k]['mcnemar_payviol_blocked'], ensure_ascii=False)}")
    (OUT / "agreement.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
    (OUT / "AGREEMENT.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=int, choices=[1, 2])
    ap.add_argument("--step", required=True, choices=["extract", "eval", "precheck", "agree"])
    ap.add_argument("--sample", default="sealed", choices=["sealed", "validation"], help="precheck step only")
    ap.add_argument("--precheck-budget", type=float, default=0.075, help="PRECHECK cap for this run (own ledger)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default="gpt-6-luna")
    ap.add_argument("--budget", type=float, default=0.40, help="extraction cap for this run (own ledger)")
    ap.add_argument("--m1g-budget", type=float, default=0.15, help="M1-G cap for this run (own ledger)")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    check_frozen()
    if a.step == "agree":
        return step_agree()
    if a.run is None:
        raise SystemExit("--run 1 or --run 2 is required for extract / eval")
    rd = OUT / f"run{a.run}"
    if a.step == "precheck":
        if a.sample == "validation":
            rd = ROOT / "results" / "integrated_dev_20261126" / "precheck_validation"
        return step_precheck(a, rd)
    if a.step == "extract":
        return step_extract(a, rd)
    if a.dry_run:
        raise SystemExit("the eval step has no dry run (it needs the extraction); use --step extract --dry-run")
    return step_eval(a, rd)


if __name__ == "__main__":
    main()
