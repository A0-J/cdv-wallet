"""Analysis of the v4 dev integrated runs (no model calls). Reads rows_v4_dev_{A,B}[_m1g].jsonl and *_matched.jsonl.

Tables (generated data; dev split):
  1 main     transaction type x arm: ALLOW / CLARIFY / DENY, plus 'final if the user answers every CLARIFY as the
             gold expects' (allow -> ALLOW, block -> DENY); the authority axis (grant) is not checked by these gates
  2 natural contamination (condition B vs A): episodes whose FnCTOD state before t differs between A and B, and
             transactions whose decision differs, per arm
  3 matched stockout view: intent case x arm, by pair_similarity; E2 firing on case 4 (consent on a disputed premise)
  4 reason match: for DENY on a context-violating transaction, share whose gate codes cover a gold context_reason field
  5 by number of accepted changes in the episode (0 / 1 / 2 / 3+)
  6 cluster bootstrap 95% CI (resampling source episodes; matched: pair_id) for 'context-violation ALLOW' and
             'normal ALLOW' per arm
The LLM baselines PRECHECK / SUMMARY (baselines_v4_dev.jsonl, condition A input) are joined as extra arms on the
condition-A rows when that file exists (no reason codes, so they are left out of table 4).
Output: results/extdata_20261126/ANALYSIS_v4_dev_{tag}.md
Usage: .venv/Scripts/python.exe eval/extdata/analyze_v4.py [m1g]
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "extdata_20261126"
V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4/dev")
CODE_FIELD = {"MAX_TOTAL": "Price", "MAX_TOTAL_WITH_FEES": "Price", "QUANTITY": "Quantity", "BUNDLE_MEMBER_MISSING": "Quantity",
              "SELECTED_MISSING": "Quantity", "ITEM": "Quantity", "BRAND": "Brand", "BRAND_EXCLUDED": "Brand",
              "FULFILLMENT": "Fulfillment", "DEADLINE": "Deadline"}


def jl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()] if Path(p).exists() else []


def final_after_answer(dec, expected):
    if dec != "CLARIFY":
        return dec
    return "ALLOW" if expected == "allow" else "DENY"


def boot(groups: dict, n=2000, seed=7):
    """groups: cluster -> list of 0/1; returns (point %, lo, hi)."""
    keys = list(groups)
    rng = random.Random(seed)
    tot = [sum(groups[k]) for k in keys]
    cnt = [len(groups[k]) for k in keys]
    point = 100 * sum(tot) / max(1, sum(cnt))
    vals = []
    for _ in range(n):
        idx = [rng.randrange(len(keys)) for _ in keys]
        s, c = sum(tot[i] for i in idx), sum(cnt[i] for i in idx)
        vals.append(100 * s / max(1, c))
    vals.sort()
    return round(point, 1), round(vals[int(0.025 * n)], 1), round(vals[int(0.975 * n)], 1)


def main(tag="", name="v4", split="dev", data=None):
    """Defaults = v4 dev (unchanged). name / split / data added 2026-11-27 (harness only) for the v4b eval."""
    global V4
    if data is not None:
        V4 = Path(data) / split
    sfx = f"_{tag}" if tag else ""
    eg = {g["episode_id"]: g for g in jl(V4 / "episode_gold.jsonl")}
    tg = {g["transaction_id"]: g for g in jl(V4 / "transaction_gold.jsonl")}
    md = [f"# v4 dev 통합 실행 분석 ({tag or '고정 이전: 주 M1 = 규칙 v2'}) — 생성 데이터, dev, 모델 호출 0", ""]
    rows = {c: jl(OUT / f"rows_{name}_{split}_{c}{sfx}.jsonl") for c in ("A", "B")}
    matched = {c: jl(OUT / f"rows_{name}_{split}_{c}{sfx}_matched.jsonl") for c in ("A", "B")}
    # LLM baselines (run_baselines.py, condition A input only): joined as extra arms on the A rows; no gate codes
    bl = {b["id"]: b for b in jl(OUT / f"baselines_{name}_{split}.jsonl")}
    for r in rows["A"] + matched["A"]:
        b = bl.get(r.get("transaction_id") or r.get("challenge_id"))
        if b:
            r["arms"]["PRECHECK"] = {"decision": b["precheck"], "codes": None}
            r["arms"]["SUMMARY"] = {"decision": b["summary"], "codes": None}
    arms = [a for a in (rows["A"][0]["arms"] if rows["A"] else {})]
    for cond in ("A", "B"):
        R = rows[cond]
        if not R:
            continue
        md += [f"## 1. 거래 유형별 판정 — 입력 조건 ({cond})", "",
               "| 유형 (n) | 비교군 | ALLOW | CLARIFY | DENY | 정답대로 답한 뒤 ALLOW |", "|---|---|---:|---:|---:|---:|"]
        by = defaultdict(list)
        for r in R:
            by[r["transaction_type"]].append(r)
        for tt in ("normal", "context_only", "both", "authority_only"):
            G = by.get(tt, [])
            for a in [x for x in arms if G and x in G[0]["arms"]]:
                c = Counter(r["arms"][a]["decision"] for r in G)
                fa = sum(final_after_answer(r["arms"][a]["decision"], r["expected"]) == "ALLOW" for r in G)
                md.append(f"| {tt} ({len(G)}) | {a} | {c.get('ALLOW', 0)} | {c.get('CLARIFY', 0)} | {c.get('DENY', 0)} | {fa} |")
        md.append("")
    if rows["A"] and rows["B"]:
        sa = {r["episode_id"]: r["fnctod_states"][-1]["state"] if r["fnctod_states"] else {} for r in rows["A"]}
        sb = {r["episode_id"]: r["fnctod_states"][-1]["state"] if r["fnctod_states"] else {} for r in rows["B"]}
        diff_eps = sorted(e for e in sa if sa[e] != sb.get(e))
        da = {r["transaction_id"]: r for r in rows["A"]}
        changed = Counter()
        for r in rows["B"]:
            ra = da.get(r["transaction_id"])
            if not ra:
                continue
            for a in arms:
                if a not in ra["arms"] or a not in r["arms"]:
                    continue
                if ra["arms"][a]["decision"] != r["arms"][a]["decision"]:
                    changed[(a, r["transaction_type"], ra["arms"][a]["decision"] + "->" + r["arms"][a]["decision"])] += 1
        md += ["## 2. 자연 오염: 판매자 글을 추출기에 넣었을 때 (B) 대 (A)", "",
               f"- 마지막 추출 상태가 (A)와 다른 여정: **{len(diff_eps)} / {len(sa)}**.",
               "- 판정이 바뀐 거래(비교군, 유형, 변화):", ""]
        md += [f"  - {a} / {tt} / {ch}: {v}" for (a, tt, ch), v in changed.most_common(40)] or ["  - 없음"]
        md.append("")
    for cond in ("A", "B"):
        M = matched[cond]
        if not M:
            continue
        md += [f"## 3. 매칭 품절 사례 — ({cond})", "", "| 사례 | 참조 판정 | 층 | n | " + " | ".join(arms) + " | E2 발동 |",
               "|---|---|---|---:|" + "---|" * len(arms) + "---:|"]
        by = defaultdict(list)
        for m in M:
            by[(m.get("intent_case"), m.get("reference_verdict"), m.get("pair_similarity"))].append(m)
        for (ic, rv, ps), G in sorted(by.items(), key=lambda kv: str(kv[0])):
            cells = []
            for a in arms:
                c = Counter(x["arms"][a]["decision"] for x in G if a in x["arms"])
                cells.append("/".join(f"{k[0]}{c.get(k, 0)}" for k in ("ALLOW", "CLARIFY", "DENY")))
            md.append(f"| {ic} | {rv} | {ps} | {len(G)} | " + " | ".join(cells) + f" | {sum(bool(x.get('e2_fires')) for x in G)} |")
        md.append("")
    R = rows["A"]
    if R:
        md += ["## 4. 차단 사유 일치 (조건 A, 맥락 위반 거래에서 DENY일 때 게이트 사유가 정답 context_reasons 필드를 포함)", "",
               "| 비교군 | DENY | 사유 일치 |", "|---|---:|---:|"]
        for a in arms:
            if a in ("PRECHECK", "SUMMARY"):
                continue                               # baselines give no gate reason codes
            den = [r for r in R if r["transaction_type"] in ("context_only", "both") and r["arms"][a]["decision"] == "DENY"]
            hit = 0
            for r in den:
                gold = set((tg.get(r["transaction_id"]) or {}).get("context_reasons") or [])
                got = {CODE_FIELD.get(str(c).split(":")[0]) for c in r["arms"][a].get("codes") or []} - {None}
                hit += bool(gold & got)
            md.append(f"| {a} | {len(den)} | {hit} |")
        md += ["", "## 5. 수용된 변경 횟수별 (조건 A): 정상 거래 ALLOW / 맥락 위반 거래 ALLOW", "", "| 변경 수 | 비교군 | 정상 ALLOW | 맥락 위반 ALLOW |",
               "|---|---|---|---|"]
        def nchg(e):
            k = len((eg.get(e) or {}).get("accepted_changes") or [])
            return "3+" if k >= 3 else str(k)
        for k in ("0", "1", "2", "3+"):
            G = [r for r in R if nchg(r["episode_id"]) == k]
            for a in arms:
                n_ = [r for r in G if r["transaction_type"] == "normal"]
                v_ = [r for r in G if r["transaction_type"] == "context_only"]
                md.append(f"| {k} | {a} | {sum(r['arms'][a]['decision'] == 'ALLOW' for r in n_)}/{len(n_)} | "
                          f"{sum(r['arms'][a]['decision'] == 'ALLOW' for r in v_)}/{len(v_)} |")
        md += ["", "## 6. 원본 여정 단위 군집 부트스트랩 95% CI (조건 A, 2,000회)", "", "| 비교군 | 맥락 위반 ALLOW % [CI] | 정상 ALLOW % [CI] |", "|---|---|---|"]
        for a in arms:
            gv, gn = defaultdict(list), defaultdict(list)
            for r in R:
                src = ((eg.get(r["episode_id"]) or {}).get("source") or {}).get("episode_id") or r["episode_id"]
                if r["transaction_type"] == "context_only":
                    gv[src].append(int(r["arms"][a]["decision"] == "ALLOW"))
                elif r["transaction_type"] == "normal":
                    gn[src].append(int(r["arms"][a]["decision"] == "ALLOW"))
            p1, p2 = boot(gv), boot(gn)
            md.append(f"| {a} | {p1[0]} [{p1[1]}, {p1[2]}] | {p2[0]} [{p2[1]}, {p2[2]}] |")
    (OUT / f"ANALYSIS_{name}_{split}{sfx}.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md[:60]))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("tag", nargs="?", default="")
    ap.add_argument("--name", default="v4")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--data", default=None)
    a = ap.parse_args()
    main(a.tag, a.name, a.split, a.data)
