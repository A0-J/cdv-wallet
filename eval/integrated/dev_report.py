"""Report for the validation development evaluation (reads dev_rows.jsonl = run2; no model calls, no rerun).

Main result: RIGHT/RIGHT_BY_LUCK journeys, per arm ALLOW / ALLOW(unverified condition) / CLARIFY by cause / DENY.
  'ALLOW (unverified condition)': ALLOW whose signed mandate carries fulfillment or deadline, which the cart-level
  payment request cannot show (recorded as unverified, never counted as satisfied).
Tests: journey-level exact McNemar on 'blocked' (CLARIFY or DENY): B3 vs B4, B3 vs B1 (and B3 vs B2).
WRONG/WRONG_HIDDEN: split into the subset the U reference blocks and the rest; reported as decisions, NOT as a
  detection rate (most WRONG carts break no payment-checkable condition).
B2 vs B3: every journey where the two decisions differ, by cause (verification / product kind / selection S).
Output: results/integrated_dev_20261126/DEV_REPORT.md, dev_report.json
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "integrated"))
from arms import raw_ctx  # noqa: E402
from cdv.v2.integrate import scope_from  # noqa: E402

DEV = ROOT / "results" / "integrated_dev_20261126"
ARMS = ("B0", "B1", "B2", "B3", "B4", "B3_v2", "v1", "AV0", "AV1", "AV2")
LEGIT, VIOL = {"RIGHT", "RIGHT_BY_LUCK"}, {"WRONG", "WRONG_HIDDEN"}


def mcnemar(a, b):
    x = sum(1 for p, q in zip(a, b) if p and not q)
    y = sum(1 for p, q in zip(a, b) if q and not p)
    n = x + y
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(x, y) + 1)) / 2 ** n)
    return {"first_only": x, "second_only": y, "p_exact": round(p, 4)}


def cause(a):
    d, codes = a["decision"], [str(c) for c in a.get("codes") or []]
    if d == "ALLOW":
        return "ALLOW"
    if d == "CLARIFY":
        if a.get("m1_asks"):
            return "CLARIFY:M1"
        if any(c.startswith("SELECTION_MISMATCH") for c in codes):
            return "CLARIFY:selection"
        if any(c.startswith("UNKNOWN_ATTR") for c in codes):
            return "CLARIFY:unknown_attr"
        if any(c.startswith("E2_") for c in codes):
            return "CLARIFY:E2"
        return "CLARIFY:other_gate"
    return "DENY"


def diff_cause(r):
    """Why B2 and B3 decide differently."""
    b2, b3 = r["arms"]["B2"], r["arms"]["B3"]
    c3 = [str(c) for c in b3.get("codes") or []]
    c2 = [str(c) for c in b2.get("codes") or []]
    if b3.get("m1_asks"):
        return "verification: unresolved M1 item changes the decision"
    if any(c.startswith(("SELECTION_MISMATCH", "ITEM:", "SELECTED_MISSING")) for c in c3):
        return "selection S"
    if any(c.startswith("UNKNOWN_ATTR:kind") for c in c3):
        return "product kind"
    if b2["decision"] != "ALLOW" and b3["decision"] == "ALLOW":
        return "verification: B2 used an unverified extractor value (" + ",".join(sorted({c.split(':')[0] for c in c2 if c != 'OUT_OF_SCOPE'})) + ")"
    return "verification: verified ledger differs (" + ",".join(sorted({c.split(':')[0] for c in c3 if c != 'OUT_OF_SCOPE'})) + ")"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    sfx = f"_{a.tag}" if a.tag else ""
    rows = [json.loads(l) for l in (DEV / f"dev_rows{sfx}.jsonl").read_text(encoding="utf-8").splitlines() if l]
    ext = {}
    for s in ("V1", "V3", "V2"):
        for l in (DEV / f"extract_{s}.jsonl").read_text(encoding="utf-8").splitlines():
            x = json.loads(l)
            ext[x["episode_id"]] = x
    # deferred (unverified) conditions in each arm's mandate (run2 rows lack B2's; consent-check rows carry them)
    for r in (rows if not a.tag else []):
        x = ext[r["episode_id"]]
        st = sorted([{"seq": int(s["turn_id"][1:]), "state": s["state"]} for s in x["fnctod_states"]
                     if int(s["turn_id"][1:]) < x["t"]], key=lambda s: s["seq"])
        r["arms"]["B2"]["deferred"] = scope_from(raw_ctx(st), None).deferred()
        for a in ("B0", "B1"):
            r["arms"][a]["deferred"] = []          # their mandate is the signed cart only
        r["arms"]["v1"]["deferred"] = []          # PLAN_v3 M2a has no fulfillment/deadline field
    rep = {"n": len(rows), "main_legit": {}, "unverified_share": {}, "mcnemar_legit_blocked": {}, "wrong": {}, "b2_vs_b3": {}}
    L = [r for r in rows if r["outcome"] in LEGIT]
    for a in ARMS:
        cnt = Counter()
        for r in L:
            c = cause(r["arms"][a])
            if c == "ALLOW" and r["arms"][a].get("deferred"):
                c = "ALLOW(unverified condition)"
            cnt[c] += 1
        rep["main_legit"][a] = dict(cnt)
        rep["unverified_share"][a] = round(100 * sum(1 for r in rows if r["arms"][a].get("deferred")) / len(rows), 1)
    blk = lambda G, a: [r["arms"][a]["decision"] != "ALLOW" for r in G]  # noqa: E731
    for a, b in (("B3", "B4"), ("B3", "B1"), ("B3", "B2")):
        rep["mcnemar_legit_blocked"][f"{a} vs {b}"] = mcnemar(blk(L, a), blk(L, b))
    W = [r for r in rows if r["outcome"] in VIOL]
    for name, G in (("U_blocks", [r for r in W if r["U_reference"]["decision"] != "ALLOW"]),
                    ("U_allows", [r for r in W if r["U_reference"]["decision"] == "ALLOW"])):
        rep["wrong"][name] = {"n": len(G), **{a: dict(Counter(r["arms"][a]["decision"] for r in G)) for a in ARMS}}
    D = [r for r in rows if r["arms"]["B2"]["decision"] != r["arms"]["B3"]["decision"]]
    rep["b2_vs_b3"] = {"n_differ": len(D),
                       "by_cause": dict(Counter((("legit" if r["outcome"] in LEGIT else "wrong"),
                                                 f"B2 {r['arms']['B2']['decision']} -> B3 {r['arms']['B3']['decision']}",
                                                 diff_cause(r)) for r in D).most_common())}
    rep["b2_vs_b3"]["by_cause"] = [{"group": k[0], "change": k[1], "cause": k[2], "n": v} for k, v in rep["b2_vs_b3"]["by_cause"].items()]
    (DEV / f"dev_report{sfx}.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    # markdown
    cols = ["ALLOW", "ALLOW(unverified condition)", "CLARIFY:M1", "CLARIFY:selection", "CLARIFY:unknown_attr",
            "CLARIFY:E2", "CLARIFY:other_gate", "DENY"]
    TAG = "[개발 분할(validation), 정책 두 가지 조정 후]"
    md = [f"# 개발 평가 보고 (validation, {sfx[1:] or 'run2'}; 개발 단계 결과)", "",
          "모든 표: " + TAG + " — 브랜드 판정(상품명 일치), 선택 불일치만 있으면 CLARIFY. 최종 결과가 아니다.", "",
          f"{TAG} 정상(RIGHT/RIGHT_BY_LUCK) {len(L)}여정, 비교군별 판정. 'ALLOW(미검증 조건 있음)' = 서명된 Mandate에 수령 방식·기한이 있으나 장바구니 단계 결제 요청에 그 정보가 없어 검사하지 못하고 통과한 경우(충족으로 세지 않음).", "",
          "| 비교군 | " + " | ".join(cols) + " |", "|---|" + "---:|" * len(cols)]
    for a in ARMS:
        md.append(f"| {a} | " + " | ".join(str(rep["main_legit"][a].get(c, 0)) for c in cols) + " |")
    md += ["", "- 주석: **B1(M1 Only)은 결제 시점 강제가 없어 DENY를 낼 수 없다**(구조상 0). B0은 공통 결제 보안만 있는 바닥값이다. v1은 PLAN_v3 규칙 + M2a 연결 행이다.",
           "- 수령 방식·기한 조건이 Mandate에 있는 여정 비율(전체 306): " + ", ".join(f"{a} {rep['unverified_share'][a]}%" for a in ("B2", "B3", "B4")) + " (B0·B1은 Mandate가 장바구니 서명뿐이라 해당 없음).",
           "", "## 여정 단위 McNemar (정상 여정, 차단 = CLARIFY 또는 DENY) " + TAG, "",
           "| 비교 | 앞쪽만 차단 | 뒤쪽만 차단 | p(정확) |", "|---|---:|---:|---:|"]
    for k, v in rep["mcnemar_legit_blocked"].items():
        md.append(f"| {k} | {v['first_only']} | {v['second_only']} | {v['p_exact']} |")
    md += ["", "## WRONG/WRONG_HIDDEN 여정 (탐지율로 해석하지 않음) " + TAG, "",
           "| 부분집합 | n | " + " | ".join(ARMS) + " |", "|---|---:|" + "---|" * len(ARMS)]
    for k, v in rep["wrong"].items():
        md.append(f"| {'U 참고값이 막음' if k == 'U_blocks' else 'U 참고값도 통과'} | {v['n']} | " +
                  " | ".join(" / ".join(f"{d[0]}{v[a].get(d, 0)}" for d in ("ALLOW", "CLARIFY", "DENY")) for a in ARMS) + " |")
    md += ["", "- 'U 참고값도 통과' 여정은 결제 시점에 검사할 수 있는 진술 조건(예산·수량·브랜드·묶음 수)을 어기지 않았다. 이 여정의 CLARIFY/DENY는 위반 탐지가 아니다.",
           "", f"## B2(M2 Only)와 B3(M1+M2)의 판정이 다른 여정: {rep['b2_vs_b3']['n_differ']} " + TAG, "",
           "| 집단 | 판정 변화 | 원인 | 여정 |", "|---|---|---|---:|"]
    for x in rep["b2_vs_b3"]["by_cause"]:
        md.append(f"| {x['group']} | {x['change']} | {x['cause']} | {x['n']} |")
    (DEV / f"DEV_REPORT{sfx}.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
