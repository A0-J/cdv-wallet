"""Descriptive analyses on v4 dev (no model calls; frozen code 610a97c): selective re-confirmation, conditional
clauses, run-to-run consistency. Rows: R-v4g (rows_v4_dev_A_m1g[_matched].jsonl). M1-G answers needed to rebuild the
B3 mandate are REPLAYED from results/extdata_20261126/ledger_m1g_v4.jsonl (a request not in the ledger is a miss:
never sent; that transaction is reported as not rebuilt).

  6 selective re-confirmation  B3 vs B4: unresolved items, combinations evaluated, approximation, why it asked, final
                                decision; transactions whose decision the unverified-at-consent policy changed
  5 conditional clauses         per arm (B2, B3, B4; AV0-AV2 and PRECHECK have no clauses by construction): clauses
                                created (mandate.fallbacks), fired (CLAUSE_ACTIVE), evidence failures by code;
                                B2 builds no selection S (raw_ctx selection None)
  4 consistency                 PRECHECK run 1 vs run 2 transition matrices by type (independent repeat, separate
                                ledgers); B2 / B3: cache reproduction only (same extraction replayed) - stored decision
                                vs recomputed decision on a sample, labelled as reproduction, not as an independent repeat
Output: results/review_20261127/selective_clauses/{SELECTIVE_CLAUSES.md, selective_clauses.json}
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check", "eval/extdata", "eval/review"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import arms as A  # noqa: E402
import run_ext as RX  # noqa: E402
from replay import Replay  # noqa: E402  (ledger-only replay client)
from cdv.v2.m1g_path import run_m1g_path  # noqa: E402

X = ROOT / "results" / "extdata_20261126"
OUT = ROOT / "results" / "review_20261127" / "selective_clauses"
V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4/dev")
NAME, SPLIT, M1G_LEDGER = "v4", "dev", "v4"
EVID = ("EVIDENCE_MISSING", "E1_", "E2_", "E3_", "CLAUSE_MISMATCH", "UNKNOWN_ATTR")


def jl(p):
    p = Path(p)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def main(tag="m1g", n_rebuild=None):
    OUT.mkdir(parents=True, exist_ok=True)
    rows = jl(X / f"rows_{NAME}_{SPLIT}_A_{tag}.jsonl")
    mrows = jl(X / f"rows_{NAME}_{SPLIT}_A_{tag}_matched.jsonl")
    eps = {e["episode_id"]: e for e in jl(V4 / "episodes.jsonl")}
    txs = {t["transaction_id"]: t for t in jl(V4 / "transactions.jsonl")}
    mx = {m["challenge_id"]: m for m in jl(V4 / "matched_stockout.jsonl")}
    tg = {g["transaction_id"]: g for g in jl(V4 / "transaction_gold.jsonl")}
    res, md = {}, [f"# 선택적 재확인·조건부 조항·반복 일관성 (v4 dev 조건 A, 고정 코드 행 `{tag}`, 모델 호출 0)", ""]

    # ---- 6 selective re-confirmation
    tab = defaultdict(Counter)
    combos, approx, policy = [], 0, Counter()
    for r in rows:
        b3, b4 = r["arms"]["B3"], r["arms"]["B4"]
        k = len(r["m1"]["unresolved"])
        kb = "0" if k == 0 else ("1" if k == 1 else ("2" if k == 2 else "3+"))
        tab[(r["transaction_type"], kb)][(b3["decision"], b4["decision"])] += 1
        combos.append(b3.get("combos") or 0)
        approx += bool(b3.get("approx"))
        if any(str(c).startswith("UNVERIFIED_AT_CONSENT") for c in b3.get("codes") or []):
            policy[(r["transaction_type"], "B3 동의 시점 확인(정책)")] += 1
        if b3.get("proceed_unverified"):
            policy[(r["transaction_type"], "B3 진행 허용(미검증)")] += 1
    why_b3 = Counter()
    for r in rows:
        b3 = r["arms"]["B3"]
        if b3["decision"] == "CLARIFY":
            why_b3["M1 확인(판정을 바꾸는 미확정 항목)" if b3.get("m1_asks") else
                   ("동의 시점 미검증(정책)" if any(str(c).startswith("UNVERIFIED") for c in b3.get("codes") or []) else
                    "게이트 확인(" + ",".join(sorted({str(c).split(':')[0] for c in b3.get('codes') or []})) + ")")] += 1
    kinds = Counter(u[1] for r in rows for u in r["m1"]["unresolved"])
    cs = sorted(combos)
    res["selective"] = {"combos_median": cs[len(cs) // 2], "combos_max": cs[-1], "approx": approx,
                        "unresolved_kinds": dict(kinds), "b3_clarify_reasons": dict(why_b3),
                        "policy": {"|".join(k): v for k, v in policy.items()},
                        "table": {f"{k[0]}|{k[1]}": {f"{a}/{b}": v for (a, b), v in c.items()} for k, c in sorted(tab.items())}}
    md += ["## 6. 선택적 재확인: B3 대 B4", "",
           f"- 거래당 조합 평가 수 중앙값 {res['selective']['combos_median']}, 최대 {res['selective']['combos_max']}; 근사 탐색(조합 64 초과) {approx}건.",
           "- 미확정 항목 종류(거래 합): " + ", ".join(f"{k} {v}" for k, v in kinds.most_common()),
           "- B3 CLARIFY 사유: " + ", ".join(f"{k} {v}" for k, v in why_b3.most_common()),
           "- 미검증 조건 정책으로 판정이 달라진 거래: " + (", ".join(f"{k[0]} / {k[1]} {v}" for k, v in sorted(policy.items())) or "없음"), "",
           "| 유형 | 미확정 수 | n | (B3 판정 / B4 판정): 건수 |", "|---|---|---:|---|"]
    for (tt, kb), c in sorted(tab.items()):
        md.append(f"| {tt} | {kb} | {sum(c.values())} | " + ", ".join(f"{a}/{b}: {v}" for (a, b), v in c.most_common()) + " |")
    md.append("")

    # ---- 5 conditional clauses
    llm = Replay(X / f"ledger_m1g_{M1G_LEDGER}.jsonl")
    clause_tab = defaultdict(Counter)
    sample = rows if n_rebuild is None else random.Random(20261127).sample(rows, min(n_rebuild, len(rows)))
    rebuilt_fail = 0
    for kind, R in (("tx", sample), ("matched", mrows)):
        by_ep = {r["episode_id"]: r for r in rows}
        for r in R:
            src = r if kind == "tx" else by_ep.get(r["episode_id"])
            if src is None:
                continue
            tx = txs[r["transaction_id"]] if kind == "tx" else mx[r["challenge_id"]]
            case = RX.build_case(eps[r["episode_id"]], tx, (tg.get(r.get("transaction_id")) or {}) if kind == "tx" else {})
            env = A.Env(case)
            st = sorted([{"seq": int(s["turn_id"][1:]), "state": s["state"]} for s in src["fnctod_states"] if int(s["turn_id"][1:]) < case.t],
                        key=lambda s: s["seq"])
            mk = lambda ctx: A.ledger_to_mandate(ctx, case.reg, case.seller, f"m-{case.episode_id}", 1, env.session)  # noqa: E731
            n_b2 = len(mk(A.raw_ctx(st)).fallbacks)
            brands = sorted({str(b) for s in st for k in ("brand_include", "brand_exclude")
                             for b in ((s["state"].get(A.PC) or {}).get(k) or [])})
            m0 = llm.misses
            try:
                m1r = run_m1g_path(st, case.user_turns, case.agent_turns, case.reg, case.t, llm, known_brands=brands)
                n_b3 = len(mk(m1r.ctx).fallbacks) if llm.misses == m0 else None
                sel = bool(m1r.ctx.selection)
            except RuntimeError:
                n_b3, sel = None, None
            if n_b3 is None:
                rebuilt_fail += 1
            for arm, n_cl in (("B2", n_b2), ("B3", n_b3), ("B4", n_b3)):
                a = r["arms"][arm]
                codes = [str(c) for c in a.get("codes") or []]
                c = clause_tab[(kind, arm)]
                c["거래"] += 1
                if n_cl is None:
                    c["조항 수 재구성 실패"] += 1
                else:
                    c["조항 생성(1개 이상)"] += n_cl > 0
                    c["조항 합계"] += n_cl
                c["발동(CLAUSE_ACTIVE)"] += "CLAUSE_ACTIVE" in codes
                for code in codes:
                    if code.startswith(EVID):
                        c["증거·조항 실패: " + code.split(":")[0]] += 1
                if arm == "B3" and sel is not None:
                    c["선택 S 있음"] += sel
            clause_tab[(kind, "B2")]["선택 S 있음"] += 0          # B2: raw_ctx has no selection by construction
    res["clauses"] = {f"{k[0]}|{k[1]}": dict(v) for k, v in clause_tab.items()}
    res["replay"] = {"hits": llm.hits, "misses": llm.misses, "not_rebuilt": rebuilt_fail}
    md += ["## 5. 조건부 조항 (AV0–AV2·AV2+·PRECHECK는 구조상 조항이 없다)", "",
           f"- B3 mandate 재구성: M1-G 원장 재생 적중 {llm.hits}, 원장에 없는 요청 {llm.misses}(보내지 않음), 재구성 실패 거래 {rebuilt_fail}.",
           "- B2는 선택 상태 S를 만들지 않는다(`raw_ctx`의 selection = None). 그래서 선택에 묶인 조항·범위 검사는 B2에서 생기지 않는다.", "",
           "| 대상 | 비교군 | 항목 | 건수 |", "|---|---|---|---:|"]
    for (kind, arm), c in sorted(clause_tab.items()):
        for k, v in sorted(c.items()):
            md.append(f"| {kind} | {arm} | {k} | {v} |")
    md.append("")

    # ---- 4 consistency
    a1 = {x["id"]: x for x in jl(X / f"baselines_{NAME}_{SPLIT}.jsonl")}
    a2 = {x["id"]: x for x in jl(X / f"baselines_{NAME}_{SPLIT}_run2.jsonl")}
    tr = defaultdict(Counter)
    for i in set(a1) & set(a2):
        tr[(a1[i]["kind"], str(a1[i]["type"]))][(a1[i]["precheck"], a2[i]["precheck"])] += 1
    res["precheck_repeat"] = {f"{k[0]}|{k[1]}": {f"{a}->{b}": v for (a, b), v in c.items()} for k, c in tr.items()}
    p4 = {r["transaction_id"]: r for r in jl(X / "rows_v4_dev_A.jsonl")} if (NAME, SPLIT) == ("v4", "dev") else {}
    rep = Counter()
    for r in rows:
        o = p4.get(r["transaction_id"])
        if o:
            rep[("B2", r["arms"]["B2"]["decision"] == o["arms"]["B2"]["decision"])] += 1
    res["b2_cache_reproduction_vs_p4"] = {f"{k[0]}|{'same' if k[1] else 'differs'}": v for k, v in rep.items()}
    md += ["## 4. 반복 일관성 (단위: 같은 거래의 최종 결제 판정)", "",
           "- PRECHECK: 독립 반복(별도 원장, 재사용 없음) 1회차 → 2회차 전이:", "",
           "| 유형 | n | 일치 | 전이(1회차→2회차) |", "|---|---:|---:|---|"]
    for (kind, tt), c in sorted(tr.items()):
        n = sum(c.values())
        same = sum(v for (a, b), v in c.items() if a == b)
        md.append(f"| {kind} {tt} | {n} | {same} | " + ", ".join(f"{a}→{b} {v}" for (a, b), v in sorted(c.items()) if a != b) + " |")
    md += ["", "- B2·B3: v4 dev에서는 **독립 반복이 없다**. R-v4g의 추출은 P4 추출을 원장에서 재사용한 캐시 재현이다.",
           f"  - 고정 전 P4 행 대 R-v4g 행의 B2 판정: " + ", ".join(f"{k} {v}" for k, v in res["b2_cache_reproduction_vs_p4"].items())
           + ". 차이가 있으면 그 사이의 정책 변경(동의 시점 미검증 → CLARIFY) 때문이고, 모델 변동이 아니다.",
           "  - B2·B3의 독립 반복은 봉인 표본 2회 실행(계획 A)에서 잰다. v4 dev에서 따로 재려면 추출과 M1-G를 새 원장으로 다시 불러야 한다(약 $0.41, 승인 필요).", ""]
    (OUT / "selective_clauses.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (OUT / "SELECTIVE_CLAUSES.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))




def _cli():
    """--data <dataset root> --name <label> --split <split> --m1g-ledger <label>: defaults = v4 dev (as before)."""
    import argparse
    global V4, NAME, SPLIT, M1G_LEDGER, OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("tag", nargs="?", default="m1g")
    ap.add_argument("--data", default=None)
    ap.add_argument("--name", default="v4")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--m1g-ledger", default=None, help="label of ledger_m1g_<label>.jsonl (default: --name)")
    a = ap.parse_args()
    NAME, SPLIT = a.name, a.split
    M1G_LEDGER = a.m1g_ledger or a.name
    if a.data:
        V4 = Path(a.data) / a.split
    if (NAME, SPLIT) != ("v4", "dev"):
        OUT = OUT.parent / f"{OUT.name}_{NAME}_{SPLIT}"
    return a.tag

if __name__ == "__main__":
    main(_cli())
