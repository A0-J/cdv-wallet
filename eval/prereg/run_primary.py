"""Run the pre-registered primary comparisons (results/frozen_610a97c/PREREG_PRIMARY.md) with primary_stats.py.

Family F1 (v4b eval; the same code runs on v4 dev as a development trial):
  rows_{name}_{split}_A_{tag}.jsonl            B2, B3, B4, AV2 (natural path, condition A)
  baselines_{name}_{split}.jsonl                PRECHECK (condition A); 'precheck' is the decision used
  rows_{name}_{split}_A_{tag}_matched.jsonl     matched challenges (intent_case 4 = false-premise consent)
  contamination_{split}{ctag}_rows.jsonl        fault-injection decisions ('M2 Only (all ops)' = B2,
                                                'M1+M2 [M1-G] B3-type' = B3) on follows_rejected_proposal transactions
  clusters: episode_gold.source.episode_id (original CartTrace journey); matched: pair_id
Family F2 (sealed sample, run 1): dev_rows_run1.jsonl (+ precheck_run1.jsonl); unit = journey; cluster = journey.
Every decision of an endpoint's population must exist for both arms; missing or ERROR units are dropped and counted.
Output: <out>/PRIMARY_<family>.md, primary_<family>.json
Usage: F1 .venv/Scripts/python.exe eval/prereg/run_primary.py F1 --data <v4b> --name v4b --split eval --tag m1g --ctag <c> --out <dir>
       F2 .venv/Scripts/python.exe eval/prereg/run_primary.py F2 --rows <run1/dev_rows_run1.jsonl> --precheck <run1/precheck_run1.jsonl> --out <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval" / "prereg"))
import primary_stats as P  # noqa: E402

X = ROOT / "results" / "extdata_20261126"
F1_SPEC = [  # (#, label, population, X arm, Y arm, event, expectation)
    (1, "B2 대 AV2: 위반 거래 부당 허용", "context_only", "B2", "AV2", "ALLOW", "x<y"),
    (2, "B2 대 AV2: 정상 거래 허용", "normal", "B2", "AV2", "ALLOW", "x>=y"),
    (3, "B3 대 B2: 결함 주입 조건의 부당 허용", "inject_follows_rejected", "B3", "B2", "ALLOW", "x<y"),
    (4, "B3 대 B2: 자연 경로 정상 거래 허용", "normal", "B3", "B2", "ALLOW", "x<=y"),
    (5, "B3 대 B4: 정상 거래 확인 요청", "normal", "B3", "B4", "CLARIFY", "x<y"),
    (6, "B3 대 PRECHECK: 정상 거래 허용", "normal", "B3", "PRECHECK", "ALLOW", "x>y"),
    (7, "B3 대 PRECHECK: 위반 거래 부당 허용", "context_only", "B3", "PRECHECK", "ALLOW", "x>=y"),
    (8, "B3 대 PRECHECK: 거짓 전제 동의 허용", "matched_case4", "B3", "PRECHECK", "ALLOW", "x<y"),
]
F2_SPEC = [
    (1, "B2 대 AV2: 위반 부당 허용", "pay_viol", "B2", "AV2", "ALLOW", "x<y"),
    (2, "B2 대 AV2: 정상 허용", "legit", "B2", "AV2", "ALLOW", "x>=y"),
    (4, "B3 대 B2: 정상 허용", "legit", "B3", "B2", "ALLOW", "x<=y"),
    (5, "B3 대 B4: 정상 확인 요청", "legit", "B3", "B4", "CLARIFY", "x<y"),
    (6, "B3 대 PRECHECK: 정상 허용", "legit", "B3", "PRECHECK", "ALLOW", "x>y"),
    (7, "B3 대 PRECHECK: 위반 부당 허용", "pay_viol", "B3", "PRECHECK", "ALLOW", "x>=y"),
]


def jl(p):
    p = Path(p)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def f1_units(a) -> dict:
    eg = {g["episode_id"]: g for g in jl(Path(a.data) / a.split / "episode_gold.jsonl")}
    src = lambda e: ((eg.get(e) or {}).get("source") or {}).get("episode_id") or e  # noqa: E731
    pre = {x["id"]: x["precheck"] for x in jl(X / f"baselines_{a.name}_{a.split}.jsonl")}
    pops = {"normal": [], "context_only": [], "matched_case4": [], "inject_follows_rejected": []}
    for r in jl(X / f"rows_{a.name}_{a.split}_A_{a.tag}.jsonl"):
        if r["transaction_type"] in ("normal", "context_only"):
            arms = {k: v["decision"] for k, v in r["arms"].items()}
            if r["transaction_id"] in pre:
                arms["PRECHECK"] = pre[r["transaction_id"]]
            pops[r["transaction_type"]].append({"unit": r["transaction_id"], "cluster": src(r["episode_id"]), "arms": arms})
    for m in jl(X / f"rows_{a.name}_{a.split}_A_{a.tag}_matched.jsonl"):
        if m.get("intent_case") == 4:
            arms = {k: v["decision"] for k, v in m["arms"].items()}
            if m["challenge_id"] in pre:
                arms["PRECHECK"] = pre[m["challenge_id"]]
            pops["matched_case4"].append({"unit": m["challenge_id"], "cluster": m["pair_id"], "arms": arms})
    cdir = Path(a.cdir) if a.cdir else ROOT / "results" / "v4check_20261126"
    for r in jl(cdir / f"contamination_{a.split}{('_' + a.ctag) if a.ctag else ''}_rows.jsonl"):
        if "follows_rejected_proposal" in r["groups"]:
            d = r["decisions"]
            pops["inject_follows_rejected"].append({"unit": r["transaction_id"], "cluster": src(r["episode_id"]),
                                                    "arms": {"B2": d.get("M2 Only (all ops)"), "B3": d.get("M1+M2 [M1-G] B3-type")}})
    return pops


def f2_units(a) -> dict:
    pre = {x["episode_id"]: x["precheck"] for x in jl(a.precheck)} if a.precheck else {}
    seen, pops = set(), {"legit": [], "pay_viol": []}
    for r in jl(a.rows):
        if r["episode_id"] in seen:
            continue
        seen.add(r["episode_id"])
        arms = {k: v["decision"] for k, v in r["arms"].items()}
        if r["episode_id"] in pre:
            arms["PRECHECK"] = pre[r["episode_id"]]
        u = {"unit": r["episode_id"], "cluster": r["episode_id"], "arms": arms}
        if r["outcome"] in ("RIGHT", "RIGHT_BY_LUCK"):
            pops["legit"].append(u)
        if r["pay_viol"]:
            pops["pay_viol"].append(u)
    return pops


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("family", choices=["F1", "F2"])
    ap.add_argument("--data")
    ap.add_argument("--name")
    ap.add_argument("--split")
    ap.add_argument("--tag", default="m1g")
    ap.add_argument("--ctag", default="")
    ap.add_argument("--cdir", default=None)
    ap.add_argument("--rows")
    ap.add_argument("--precheck", default=None)
    ap.add_argument("--label", default="", help="e.g. '고정 후 dev 시험' or '최종 평가'")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pops, spec = (f1_units(a), F1_SPEC) if a.family == "F1" else (f2_units(a), F2_SPEC)
    results, dropped = [], {}
    for num, lab, pop, x, y, ev, exp in spec:
        U = [u for u in pops[pop] if u["arms"].get(x) not in (None, "ERROR") and u["arms"].get(y) not in (None, "ERROR")]
        dropped[num] = len(pops[pop]) - len(U)
        r = P.endpoint(U, x, y, ev)
        r.update(num=num, label=lab, population=pop, expect=exp)
        results.append(r)
    P.holm([r for r in results if r.get("n")])
    md = [f"# 1차 비교 {a.family} ({a.label}) — 사전 지정(PREREG_PRIMARY.md), Holm 가족 내 {len(results)}개", "",
          "| # | 비교 | 모집단 n (군집) | X 사건 | Y 사건 | 차이 %p [95% CI] | p(순열) | p(Holm) | 판정 | 제외 |",
          "|---|---|---|---|---|---|---:|---:|---|---:|"]
    for r in results:
        if not r.get("n"):
            md.append(f"| {r['num']} | {r['label']} | 0 | - | - | - | - | - | 자료 없음 | {dropped[r['num']]} |")
            continue
        md.append(f"| {r['num']} | {r['label']} | {r['n']} ({r['clusters']}) | {r['x_count']}/{r['n']} ({r['x_pct']}%) | "
                  f"{r['y_count']}/{r['n']} ({r['y_pct']}%) | {r['diff_pp']} [{r['ci95'][0]}, {r['ci95'][1]}] | {r['p_perm']} | "
                  f"{r['p_holm']} | {P.verdict(r, r['expect'])} | {dropped[r['num']]} |")
    md += ["", "- 차이 = X − Y(%p). 예상 방향: 사전 지정 표. 단위 수준 McNemar p는 json에 있다."]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"primary_{a.family}.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (out / f"PRIMARY_{a.family}.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
