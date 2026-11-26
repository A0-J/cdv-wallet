"""EXPLORATORY trade-off analysis (not a pre-registered comparison; no Holm): PRECHECK vs the proposed structure on
v4 dev. No model calls. Reads the frozen-code rows of R-v4g (rows_v4_dev_{A,B}_m1g[_matched].jsonl; B3 = M1-G main)
and the PRECHECK runs (baselines_v4_dev.jsonl = A run 1, baselines_v4_dev_B.jsonl = B, baselines_v4_dev_run2.jsonl).

  1  AV2 vs B2 on context_only: transactions AV2 allows and B2 does not, by the component that blocked in B2 (gate
     codes) and by the gold context_reasons field; the adjustment-history item that introduced each component; an
     upper bound of what the post-hoc adjustments contribute (transactions blocked ONLY by components added by
     adjustments made on development data)
  2  PRECHECK / B2 / B3 (+ AV2, B4) ALLOW/CLARIFY/DENY on normal / context_only / both, conditions A and B;
     auxiliary: 'final if every CLARIFY is answered as the gold expects'
  3  false-premise consent (matched intent_case 4, reference CLARIFY): ALLOW / CLARIFY / DENY per arm and condition,
     by evidence_status; 'unjustified allow prevented' = not ALLOW, 'correct re-confirmation' = CLARIFY (DENY is not
     counted as correct)
  4  repeated verification of the same mandate: per-dialogue calls / cost / latency from the ledgers, PRECHECK
     consistency (run 1 vs run 2; identical-input pairs inside run 1), deterministic gate consistency (recomputed)
Output: results/review_20261127/tradeoff/{TRADEOFF.md, tradeoff.json}
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check", "eval/extdata"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
from paired_compare import component  # noqa: E402

X = ROOT / "results" / "extdata_20261126"
OUT = ROOT / "results" / "review_20261127" / "tradeoff"
V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4/dev")
NAME, SPLIT, M1G_LEDGER = "v4", "dev", "v4"
# component label (paired_compare.COMPONENT) -> adjustment-history item that introduced it (docs/ADJUSTMENT_HISTORY.md)
ADJ = {"총액(수수료 포함)": "#14 (v4 dev)", "수령 방식(동의 시점)": "#10 (validation)", "기한(동의 시점)": "#10 (validation)",
       "동의 시점 미검증(확인)": "#18 (validation)", "정보 부족(확인)": "#6 (설계) / #15", "묶음 구성": "#7 (validation 파일럿)",
       "선택 불일치": "#9 (validation)", "조건 조항": "#14 (v4 dev)", "브랜드": "기본 (#15로 상품명 일치 제외)",
       "수량": "기본", "총액": "기본", "선택 상품 포함": "#7", "E2(판매자 주장)": "기본 설계", "A-VIP": "기본", "M1 확인": "M1"}
DEV_ADJ = {"총액(수수료 포함)", "수령 방식(동의 시점)", "기한(동의 시점)", "동의 시점 미검증(확인)", "묶음 구성", "선택 불일치",
           "조건 조항", "선택 상품 포함"}
ARMS = ("AV2", "B2", "B3", "B4", "PRECHECK")


def jl(p):
    p = Path(p)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def comps(a: dict) -> list:
    c = component(a.get("codes"), a.get("m1_asks"))
    return [x.strip() for x in c.split(",")] if c != "-" else []


def acd(G, arm):
    c = Counter(r["arms"][arm]["decision"] for r in G if arm in r["arms"])
    return c["ALLOW"], c["CLARIFY"], c["DENY"]


def main(tag="m1g"):
    OUT.mkdir(parents=True, exist_ok=True)
    tg = {g["transaction_id"]: g for g in jl(V4 / "transaction_gold.jsonl")}
    sfx = f"_{tag}" if tag else ""           # tag '' = pre-freeze P4 rows (wiring test only)
    rows = {c: jl(X / f"rows_{NAME}_{SPLIT}_{c}{sfx}.jsonl") for c in ("A", "B")}
    mrows = {c: jl(X / f"rows_{NAME}_{SPLIT}_{c}{sfx}_matched.jsonl") for c in ("A", "B")}
    pre = {"A": {x["id"]: x["precheck"] for x in jl(X / f"baselines_{NAME}_{SPLIT}.jsonl")},
           "B": {x["id"]: x["precheck"] for x in jl(X / f"baselines_{NAME}_{SPLIT}_B.jsonl")}}
    for c in ("A", "B"):
        for r in rows[c] + mrows[c]:
            d = pre[c].get(r.get("transaction_id") or r.get("challenge_id"))
            if d:
                r["arms"]["PRECHECK"] = {"decision": d, "codes": None}
    res, md = {"tag": tag, "available": {c: len(rows[c]) for c in rows}}, [
        f"# 탐색적 분석: PRECHECK 대 제안 구조의 절충 (v4 dev, 고정 코드 행 `{tag}`, 모델 호출 0)", "",
        "- **탐색적 분석이다.** 사전 지정한 1차 비교(PREREG_PRIMARY.md)와 Holm 보정 대상이 아니다.",
        "- 수치: B2·B3·B4·AV2는 [고정 후 dev](R-v4g, 주 M1 = M1-G), PRECHECK는 [고정 후 dev] 별도 실행.", ""]

    # ---- 1. AV2 vs B2 on context_only
    A_ = rows["A"]
    if A_:
        ctx = [r for r in A_ if r["transaction_type"] == "context_only"]
        av_only = [r for r in ctx if r["arms"]["AV2"]["decision"] == "ALLOW" and r["arms"]["B2"]["decision"] != "ALLOW"]
        b2_only = [r for r in ctx if r["arms"]["B2"]["decision"] == "ALLOW" and r["arms"]["AV2"]["decision"] != "ALLOW"]
        comp_c, field_c, adj_only = Counter(), Counter(), 0
        for r in av_only:
            cs = comps(r["arms"]["B2"])
            for x in cs:
                comp_c[x] += 1
            if cs and all(x in DEV_ADJ for x in cs):
                adj_only += 1
            for f in (tg.get(r["transaction_id"]) or {}).get("context_reasons") or []:
                field_c[f] += 1
        res["av2_vs_b2"] = {"context_only": len(ctx), "AV2_allow": acd(ctx, "AV2")[0], "B2_allow": acd(ctx, "B2")[0],
                            "AV2_allows_B2_blocks": len(av_only), "B2_allows_AV2_blocks": len(b2_only),
                            "by_component": dict(comp_c), "by_gold_field": dict(field_c), "blocked_only_by_dev_adjustments": adj_only}
        md += ["## 1. AV2 대 B2: 맥락 위반 거래(context_only)에서 줄어든 부당 허용의 출처 (조건 A)", "",
               f"- AV2 ALLOW {acd(ctx, 'AV2')[0]}, B2 ALLOW {acd(ctx, 'B2')[0]} (n={len(ctx)}). AV2만 허용·B2는 막음 {len(av_only)}건, "
               f"B2만 허용·AV2는 막음 {len(b2_only)}건.", "",
               "| B2에서 막은 구성 요소 | 건수 (중복 가능) | 이 요소를 넣은 조정 |", "|---|---:|---|"]
        md += [f"| {k} | {v} | {ADJ.get(k, '-')} |" for k, v in comp_c.most_common()]
        md += ["", "| 정답 context_reasons 필드 | 건수 (중복 가능) |", "|---|---:|"] + [f"| {k} | {v} |" for k, v in field_c.most_common()]
        md += ["", f"- 개발 분할 조정으로 들어온 요소만으로 막힌 거래: **{adj_only} / {len(av_only)}** "
               "(조정 전 게이트였다면 통과했을 가능성의 상한. 다른 기본 검사가 대신 잡았을 수 있어 정확한 재계산은 아니다).", ""]

    # ---- 2. main table A and B, PRECHECK / B2 / B3 / B4 / AV2
    res["main"] = {}
    for c in ("A", "B"):
        R = rows[c]
        if not R:
            continue
        md += [f"## 2. 정상·위반 거래별 판정 — 조건 ({c})", "", "| 유형 (n) | 비교군 | ALLOW | CLARIFY | DENY | 보조: 정답대로 답한 뒤 ALLOW |", "|---|---|---:|---:|---:|---:|"]
        for tt in ("normal", "context_only", "both"):
            G = [r for r in R if r["transaction_type"] == tt]
            for arm in ARMS:
                if not G or arm not in G[0]["arms"]:
                    continue
                a, cl, d = acd(G, arm)
                fin = sum(1 for r in G if r["arms"][arm]["decision"] == "ALLOW" or (r["arms"][arm]["decision"] == "CLARIFY" and r["expected"] == "allow"))
                res["main"][f"{c}|{tt}|{arm}"] = [a, cl, d, fin]
                md.append(f"| {tt} ({len(G)}) | {arm} | {a} | {cl} | {d} | {fin} |")
        md.append("")

    # ---- 3. false-premise consent (case 4)
    res["case4"] = {}
    md += ["## 3. 거짓 전제 동의(매칭 사례 4, 기준 판정 CLARIFY)", "",
           "- 부당 허용 방지 = ALLOW가 아님. 올바른 재확인 = CLARIFY. DENY는 정답으로 세지 않는다.", "",
           "| 조건 | 증거 상태 | n | 비교군 | ALLOW | CLARIFY(정답) | DENY |", "|---|---|---:|---|---:|---:|---:|"]
    for c in ("A", "B"):
        M = [m for m in mrows[c] if m.get("intent_case") == 4]
        for ev in sorted({m.get("evidence_status") for m in M}, key=str) + ["(전체)"]:
            G = M if ev == "(전체)" else [m for m in M if m.get("evidence_status") == ev]
            for arm in ARMS:
                if not G or arm not in G[0]["arms"]:
                    continue
                a, cl, d = acd(G, arm)
                res["case4"][f"{c}|{ev}|{arm}"] = [a, cl, d]
                md.append(f"| {c} | {ev} | {len(G)} | {arm} | {a} | {cl} | {d} |")
    md.append("")

    # ---- 4. repeated verification of the same mandate
    cl_ = json.loads((ROOT / "results" / "review_20261127" / "cost_latency" / "cost_latency.json").read_text(encoding="utf-8"))
    a1 = {x["id"]: x for x in jl(X / f"baselines_{NAME}_{SPLIT}.jsonl")}
    # identical-input pairs inside run 1: authority_only vs normal transactions with the same episode and the same checkout
    txs = {t["transaction_id"]: t for t in jl(V4 / "transactions.jsonl")}
    key = defaultdict(list)
    for i, x in a1.items():
        t = txs.get(i)
        if t is not None:
            key[(t["episode_id"], json.dumps(t["checkout"], sort_keys=True))].append(x["precheck"])
    groups = [v for v in key.values() if len(v) > 1]
    same_in_run = sum(1 for v in groups if len(set(v)) == 1)
    # deterministic gate: recompute B2 twice on the A rows and compare
    gate_same = None
    if A_:
        import arms as AR
        import run_ext as RX
        eps = {e["episode_id"]: e for e in jl(V4 / "episodes.jsonl")}
        diff = 0
        for r in A_[:400]:
            tx = txs[r["transaction_id"]]
            outs = []
            for _ in range(2):
                case = RX.build_case(eps[r["episode_id"]], tx, tg.get(tx["transaction_id"]) or {})
                env = AR.Env(case)
                st = sorted([{"seq": int(s["turn_id"][1:]), "state": s["state"]} for s in r["fnctod_states"] if int(s["turn_id"][1:]) < case.t],
                            key=lambda s: s["seq"])
                outs.append(env.full_gate(AR.ledger_to_mandate(AR.raw_ctx(st), case.reg, case.seller, f"m-{case.episode_id}", 1, env.session)))
            diff += outs[0] != outs[1]
        gate_same = f"{400 - diff}/400"
    res["repeat"] = {"precheck_run1_vs_run2": f"{cl_['precheck_agreement']['same']}/{cl_['precheck_agreement']['n']}",
                     "precheck_identical_input_groups_in_run1": f"{same_in_run}/{len(groups)}", "gate_recomputed_same": gate_same}
    e, m, p = cl_["extraction_A"], cl_["m1g_natural_A_so_far"], cl_["precheck_A_run1"]
    md += ["## 4. 같은 권한(대화)에 대한 반복 결제 검증", "",
           "- v4 dev는 대화 430개에 결제 요청 1,570개(대화당 평균 3.65개)다.",
           f"- 제안 구성: 권한(mandate)은 대화 중 한 번 만든다(추출 대화당 {e['calls'] / 430:.1f}회 ${e['cost_usd'] / 430:.5f}, "
           f"M1-G 대화당 {m['calls'] / 430:.1f}회 ${m['cost_usd'] / 430:.5f}). 결제 요청마다 게이트만 다시 돈다(모델 호출 0, 중앙값 "
           f"{cl_['gate_ms']['B2 gate (mandate + full M2 gate)']['median']} ms).",
           f"- PRECHECK: 결제 요청마다 1회(요청당 ${p['cost_usd'] / p['calls']:.6f}, 지연 중앙값 {p['latency_median_s']} s). "
           f"대화당 결제 k건이면 k회 호출이다.",
           f"- 일관성: PRECHECK 1회차 대 2회차 {res['repeat']['precheck_run1_vs_run2']}. "
           f"1회차 안에서 입력이 같은 결제 요청 묶음의 판정 일치 {res['repeat']['precheck_identical_input_groups_in_run1']}. "
           f"게이트를 같은 입력으로 두 번 계산한 판정 일치 {gate_same}.", ""]
    (OUT / f"tradeoff{sfx or '_prefreeze_test'}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (OUT / f"TRADEOFF{sfx or '_prefreeze_test'}.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
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
    main(_cli())   # tag "" = pre-freeze wiring test
