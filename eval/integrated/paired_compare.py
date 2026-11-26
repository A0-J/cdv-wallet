"""Paired (journey-level) comparison of arms on the validation development rows (no model calls).

For each pair of arms and each group (pay_viol = the U reference denies; legit = RIGHT/RIGHT_BY_LUCK):
  2x2 table of blocked (CLARIFY or DENY) vs not, exact McNemar on the discordant journeys, and for every discordant
  journey the gate codes of both arms mapped to the component that produced the block (codes only, no dialogue text).
Pairs: AV1 vs B2 (same extracted state = last state before t; checker differs: PLAN_v3 cart check vs M2 gate),
       AV2 vs B2 (state construction AND checker differ), B2 vs B3 (M1 added), B3 vs B4 (selective re-confirmation).
Input: results/integrated_dev_20261126/dev_rows_{tag}.jsonl
Output: results/integrated_dev_20261126/PAIRED_{tag}.md, paired_{tag}.json
Usage: .venv/Scripts/python.exe eval/integrated/paired_compare.py frozen_m1g
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "results" / "integrated_dev_20261126"
LEGIT = {"RIGHT", "RIGHT_BY_LUCK"}
PAIRS = (("AV1", "B2"), ("AV2", "B2"), ("B2", "B3"), ("B3", "B4"))
COMPONENT = [  # first matching prefix wins; the label names the part of the gate that produced the code
    ("MAX_TOTAL_WITH_FEES", "총액(수수료 포함)"), ("MAX_TOTAL", "총액"), ("BUNDLE_MEMBER_MISSING", "묶음 구성"),
    ("SELECTED_MISSING", "선택 상품 포함"), ("SELECTION_MISMATCH", "선택 불일치"), ("QUANTITY", "수량"), ("ITEM", "수량"),
    ("BRAND_EXCLUDED", "브랜드"), ("BRAND", "브랜드"), ("UNKNOWN_ATTR", "정보 부족(확인)"),
    ("UNVERIFIED_AT_CONSENT", "동의 시점 미검증(확인)"), ("FULFILLMENT", "수령 방식(동의 시점)"), ("DEADLINE", "기한(동의 시점)"),
    ("E2", "E2(판매자 주장)"), ("CLAUSE", "조건 조항"), ("NOT_CAPTURED", "A-VIP"), ("V", "A-VIP"), ("STALE", "버전"),
]


def component(codes, m1_asks=False) -> str:
    out = []
    for c in codes or []:
        c = str(c)
        if c == "OUT_OF_SCOPE":
            continue
        lab = next((l for p, l in COMPONENT if c.startswith(p)), "기타:" + c.split(":")[0])
        if lab not in out:
            out.append(lab)
    if m1_asks:
        out.append("M1 확인")
    return ", ".join(out) or "-"


def mcnemar(x: int, y: int) -> float:
    n = x + y
    return 1.0 if n == 0 else round(min(1.0, 2 * sum(math.comb(n, i) for i in range(min(x, y) + 1)) / 2 ** n), 4)


def main(tag: str):
    rows = [json.loads(l) for l in (DEV / f"dev_rows_{tag}.jsonl").read_text(encoding="utf-8").splitlines() if l]
    groups = {"pay_viol": [r for r in rows if r["pay_viol"]], "legit": [r for r in rows if r["outcome"] in LEGIT]}
    blk = lambda r, a: r["arms"][a]["decision"] != "ALLOW"  # noqa: E731
    res, md = {}, [f"# 짝지은 비교 (validation 개발 분할, `dev_rows_{tag}.jsonl`, 모델 호출 0)", "",
                   "- 차단 = CLARIFY 또는 DENY. pay_viol = 정답 조건을 넣은 U 기준이 막는 여정(우리 게이트로 정의됨).",
                   "- AV1과 B2는 같은 추출 상태(t 직전 마지막 상태)를 쓴다. 차이는 검사기(PLAN_v3 장바구니 검사 대 M2 게이트)뿐이다.",
                   "- AV2는 상태를 누적(지우지 않음)하고 검사기는 AV1과 같다. 그래서 AV2 대 B2는 상태 구성과 검사기가 함께 다르다.", ""]
    for a, b in PAIRS:
        if not rows or a not in rows[0]["arms"] or b not in rows[0]["arms"]:
            continue
        for g, G in groups.items():
            c = Counter((blk(r, a), blk(r, b)) for r in G)
            x, y = c[(True, False)], c[(False, True)]
            disc = [r for r in G if blk(r, a) != blk(r, b)]
            res[f"{a} vs {b} | {g}"] = {"n": len(G), "both": c[(True, True)], f"{a}_only": x, f"{b}_only": y,
                                        "neither": c[(False, False)], "p_exact": mcnemar(x, y)}
            md += [f"## {a} 대 {b} — {g} (n={len(G)})", "",
                   f"- 둘 다 차단 {c[(True, True)]}, {a}만 {x}, {b}만 {y}, 둘 다 통과 {c[(False, False)]}. McNemar 정확 p = {mcnemar(x, y)}.", ""]
            if disc:
                md += [f"| 여정 | {a} | {a} 차단 요소 | {b} | {b} 차단 요소 |", "|---|---|---|---|---|"]
                for r in sorted(disc, key=lambda r: (blk(r, a), r["episode_id"])):
                    ra, rb = r["arms"][a], r["arms"][b]
                    md.append(f"| `{r['episode_id'][-8:]}` | {ra['decision']} | {component(ra.get('codes'), ra.get('m1_asks'))} | "
                              f"{rb['decision']} | {component(rb.get('codes'), rb.get('m1_asks'))} |")
                comp = Counter(component(r["arms"][b].get("codes"), r["arms"][b].get("m1_asks")) for r in disc if blk(r, b))
                md += ["", f"- {b}만 막은 {y}건의 차단 요소: " + (", ".join(f"{k} {v}" for k, v in comp.most_common()) or "없음"), ""]
    (DEV / f"paired_{tag}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (DEV / f"PAIRED_{tag}.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "frozen_m1g")
