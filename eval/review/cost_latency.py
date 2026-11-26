"""Cost / tokens / latency per arm on v4 dev, and PRECHECK run-to-run agreement (no model calls).

Model calls: from the ledgers (each call: usage tokens, cost_usd, latency_s).
  extraction (FnCTOD + plain, condition A)  ledger_v4.jsonl, calls before condition B started (2026-11-26 23:53 KST)
  M1-G (natural path, condition A)          ledger_m1g_v4.jsonl (R-v4g; whatever exists when this runs)
  PRECHECK (condition A, run 1)             ledger_baselines_v4.jsonl, '"decision"' outputs before PRECHECK-B (00:39 KST)
  PRECHECK run 2                            ledger_baselines_v4_run2.jsonl
Deterministic gate time: rebuild each v4 dev transaction (run_ext.build_case) from the P4 condition-A rows and time
  B2 = full M2 gate on the raw extracted state, AV0 / AV2 = A-VIP (+ PLAN_v3 cart check), with perf_counter.
Output: results/review_20261127/cost_latency/{COST_LATENCY.md, cost_latency.json}
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check", "eval/extdata"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
OUT = ROOT / "results" / "review_20261127" / "cost_latency"
X = ROOT / "results" / "extdata_20261126"
V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4/dev")
KST = dt.timezone(dt.timedelta(hours=9))
B_START = dt.datetime(2026, 11, 26, 23, 53, tzinfo=KST).timestamp()
PB_START = dt.datetime(2026, 11, 27, 0, 39, 44, tzinfo=KST).timestamp()


def jl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def stats(calls: list) -> dict:
    if not calls:
        return {"calls": 0}
    lat = sorted(c.get("latency_s") or 0 for c in calls)
    ti = sum((c.get("usage") or {}).get("input_tokens", 0) for c in calls)
    to = sum((c.get("usage") or {}).get("output_tokens", 0) for c in calls)
    return {"calls": len(calls), "input_tokens": ti, "output_tokens": to, "cost_usd": round(sum(c.get("cost_usd") or 0 for c in calls), 6),
            "latency_median_s": round(lat[len(lat) // 2], 3), "latency_p90_s": round(lat[int(0.9 * len(lat))], 3),
            "errors": sum(1 for c in calls if c.get("error"))}


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.1f}%)" if b else "-"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ext = [c for c in jl(X / "ledger_v4.jsonl") if c["ts"] < B_START]
    m1g = jl(X / "ledger_m1g_v4.jsonl")
    bl = jl(X / "ledger_baselines_v4.jsonl")
    pre1 = [c for c in bl if c["ts"] < PB_START and '"decision"' in (c.get("output_text") or "")]
    summ = [c for c in bl if c["ts"] < PB_START and '"decision"' not in (c.get("output_text") or "")]
    pre2 = jl(X / "ledger_baselines_v4_run2.jsonl")
    res = {"extraction_A": stats(ext), "m1g_natural_A_so_far": stats(m1g), "precheck_A_run1": stats(pre1),
           "precheck_A_run2": stats(pre2), "summary_baseline": stats(summ), "episodes": 430, "transactions": 1474, "matched": 96}

    # deterministic gate timing on the P4 condition-A rows (pre-freeze extraction; the gate code is the frozen one)
    import arms as A
    import run_ext as RX
    eps = {e["episode_id"]: e for e in jl(V4 / "episodes.jsonl")}
    txs = {t["transaction_id"]: t for t in jl(V4 / "transactions.jsonl")}
    tg = {g["transaction_id"]: g for g in jl(V4 / "transaction_gold.jsonl")}
    times = defaultdict(list)
    for r in jl(X / "rows_v4_dev_A.jsonl"):
        tx = txs[r["transaction_id"]]
        ep = eps[r["episode_id"]]
        t0 = time.perf_counter()
        case = RX.build_case(ep, tx, tg.get(tx["transaction_id"]) or {})
        env = A.Env(case)
        times["case+env build"].append(time.perf_counter() - t0)
        st = sorted([{"seq": int(s["turn_id"][1:]), "state": s["state"]} for s in r["fnctod_states"] if int(s["turn_id"][1:]) < case.t],
                    key=lambda s: s["seq"])
        t0 = time.perf_counter()
        m = A.ledger_to_mandate(A.raw_ctx(st), case.reg, case.seller, f"m-{case.episode_id}", 1, env.session)
        env.full_gate(m)
        times["B2 gate (mandate + full M2 gate)"].append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        A.avip_simple(env, None)
        times["AV0 (A-VIP)"].append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        A.avip_simple(env, A.dst_acc(st))
        times["AV2 (A-VIP + cart check)"].append(time.perf_counter() - t0)
    res["gate_ms"] = {k: {"median": round(1000 * sorted(v)[len(v) // 2], 2), "p90": round(1000 * sorted(v)[int(0.9 * len(v))], 2), "n": len(v)}
                      for k, v in times.items()}
    # B3 selective combos actually evaluated (gate calls = combos) from the P4 rows
    combos = [r["arms"]["B3"].get("combos") or 1 for r in jl(X / "rows_v4_dev_A.jsonl")]
    res["b3_gate_calls_per_tx"] = {"median": sorted(combos)[len(combos) // 2], "max": max(combos)}

    # PRECHECK run-to-run agreement
    a = {x["id"]: x for x in jl(X / "baselines_v4_dev.jsonl")}
    b = {x["id"]: x for x in jl(X / "baselines_v4_dev_run2.jsonl")}
    both = sorted(set(a) & set(b))
    trans = Counter((a[i]["precheck"], b[i]["precheck"]) for i in both)
    by = defaultdict(lambda: [0, 0])
    for i in both:
        by[(a[i]["kind"], a[i]["type"])][0] += a[i]["precheck"] == b[i]["precheck"]
        by[(a[i]["kind"], a[i]["type"])][1] += 1
    res["precheck_agreement"] = {"n": len(both), "same": sum(trans[(d, d)] for d in ("ALLOW", "CLARIFY", "DENY")),
                                 "transitions": {f"{k[0]}->{k[1]}": v for k, v in sorted(trans.items())},
                                 "by_type": {f"{k[0]}|{k[1]}": f"{v[0]}/{v[1]}" for k, v in sorted(by.items(), key=lambda kv: str(kv[0]))}}
    (OUT / "cost_latency.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    e, m, p1, p2 = res["extraction_A"], res["m1g_natural_A_so_far"], res["precheck_A_run1"], res["precheck_A_run2"]
    md = ["# 호출·토큰·비용·지연 비교 (v4 dev, 모델 호출 0 — 원장 집계와 결정적 게이트 시간 측정)", "",
          "- 단위 주의: v4는 대화 하나에 결제 요청이 여러 개(거래 1,474 / 대화 430)라 '거래당'은 추출 비용을 나눠 가진 값이다. 실제 쓰임에서는 대화당 결제 1회에 가깝다.",
          "- 제안 구성의 모델 호출(턴별 추출, 변경별 M1-G)은 대화가 진행되는 동안 일어난다. 결제 시점에는 결정적 게이트만 돈다. PRECHECK는 결제 시점에 모델을 1회 부른다.", "",
          "| 구성 요소 | 호출 | 입력 토큰 | 출력 토큰 | 비용 | 호출 지연 중앙값 / p90 | 대화당 호출 | 대화당 비용 |", "|---|---:|---:|---:|---:|---|---:|---:|"]
    for name, s in (("추출(FnCTOD + 일반 추출, 조건 A, 고정 전 P4)", e), ("M1-G 근거 판정(조건 A, R-v4g)", m),
                    ("PRECHECK 1회차(조건 A)", p1), ("PRECHECK 2회차(같은 입력)", p2), ("SUMMARY 기준선(요약 + 추출)", res["summary_baseline"])):
        if s.get("calls"):
            md.append(f"| {name} | {s['calls']:,} | {s['input_tokens']:,} | {s['output_tokens']:,} | ${s['cost_usd']:.4f} | "
                      f"{s['latency_median_s']} / {s['latency_p90_s']} s | {s['calls'] / 430:.1f} | ${s['cost_usd'] / 430:.5f} |")
    md += ["", f"- PRECHECK는 거래 {res['transactions']:,} + 매칭 {res['matched']} = 1,570회(결제 요청마다 1회)다. 위 '대화당' 열은 비교를 위해 430으로 나눈 값이다.",
           f"- M1-G 행은 R-v4g가 끝나기 전의 원장일 수 있다(호출 {m.get('calls', 0)}회 시점).", "",
           "## 결정적 게이트 시간 (이 컴퓨터, 모델 호출 0, 거래 1,474)", "", "| 측정 | 중앙값 ms | p90 ms |", "|---|---:|---:|"]
    for k, v in res["gate_ms"].items():
        md.append(f"| {k} | {v['median']} | {v['p90']} |")
    md += [f"- B3의 선택적 재확인은 미해결 항목 조합마다 게이트를 다시 부른다. 거래당 조합 수 중앙값 {res['b3_gate_calls_per_tx']['median']}, 최대 {res['b3_gate_calls_per_tx']['max']}(고정 전 P4 행).", "",
           "## PRECHECK 회차 간 일치 (같은 입력, 별도 원장)", "",
           f"- 판정 일치 {pct(res['precheck_agreement']['same'], res['precheck_agreement']['n'])}.",
           "- 전이(1회차→2회차): " + ", ".join(f"{k} {v}" for k, v in res["precheck_agreement"]["transitions"].items()), "",
           "| 유형 | 일치 |", "|---|---:|"] + [f"| {k} | {v} |" for k, v in res["precheck_agreement"]["by_type"].items()]
    (OUT / "COST_LATENCY.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
