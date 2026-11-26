"""Final report by violation type (no model calls; fixed before v4b eval is opened).

For every configuration (AV0, AV1, AV2, AV2+, B1, B2, B3, B4, B3_v2, PRECHECK) and input condition (A, B):
  - ALLOW / CLARIFY / DENY per transaction type (normal, context_only, authority_only, both) with denominators
  - per violated context field (gold context_reasons; 'only' = that field alone) on context_only transactions
  - per violated authority field (gold authority_reasons) on authority_only transactions: each configuration's OWN
    decision, plus the column 'basic authority check' = the evaluation-script comparison run_ext.py::authority_check,
    the same for every configuration and NEVER added to any configuration's blocks
  - paired normal <-> authority_only and context_only <-> both on the same cart: how often the decision differs
Denominators: transactions after the exclusion of already-seen source journeys (run_ext exclusion file); dialogues
without a normal transaction are counted. Totals over types are auxiliary only (they follow the data's type mix).
Inputs: rows_{name}_{split}_{A,B}_{tag}.jsonl, baselines_{name}_{split}[_B].jsonl, AV2+ rows
results/review_20261127/av2plus[_{name}_{split}]/av2plus_rows_v4dev_{A,B}_{tag}.jsonl.
Usage: .venv/Scripts/python.exe eval/final/report_by_type.py --data <root> --name v4 --split dev [--tag m1g]
Output: results/review_20261127/by_type_{name}_{split}/{BY_TYPE.md, by_type.json}
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
X = ROOT / "results" / "extdata_20261126"
ARMS = ("AV0", "AV1", "AV2", "AV2+", "B1", "B2", "B3", "B4", "B3_v2", "PRECHECK")
TYPES = ("normal", "context_only", "authority_only", "both")


def jl(p):
    p = Path(p)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def acd(G, arm):
    c = Counter(r["arms"][arm]["decision"] for r in G if arm in r["arms"])
    return f"{c['ALLOW']}/{c['CLARIFY']}/{c['DENY']}" if c else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--tag", default="m1g")
    a = ap.parse_args()
    d = Path(a.data) / a.split
    tg = {g["transaction_id"]: g for g in jl(d / "transaction_gold.jsonl")}
    excl = set(json.loads((X / f"exclusion_{a.name}_{a.split}.json").read_text(encoding="utf-8"))["excluded_episodes"])
    av_dir = ROOT / "results" / "review_20261127" / ("av2plus" if (a.name, a.split) == ("v4", "dev") else f"av2plus_{a.name}_{a.split}")
    out_dir = ROOT / "results" / "review_20261127" / f"by_type_{a.name}_{a.split}"
    out_dir.mkdir(parents=True, exist_ok=True)
    res, md = {}, [f"# 위반 유형별 보고 ({a.name} {a.split}, 행 `{a.tag}`, 모델 호출 0)", "",
                   "- '기본 권한 대조'는 평가 스크립트(`run_ext.py::authority_check`)의 grant 대조다. 모든 구성에 같으며 시스템 게이트가 아니다. 어떤 구성의 차단 건수에도 넣지 않는다.",
                   "- 합계는 데이터의 유형 비율을 따르므로 보조로만 본다.", ""]
    for c in ("A", "B"):
        R = jl(X / f"rows_{a.name}_{a.split}_{c}_{a.tag}.jsonl")
        if not R:
            continue
        pre = {x["id"]: x["precheck"] for x in jl(X / (f"baselines_{a.name}_{a.split}.jsonl" if c == "A" else f"baselines_{a.name}_{a.split}_B.jsonl"))}
        avp = {x["transaction_id"]: x["AV2+"] for x in jl(av_dir / f"av2plus_rows_v4dev_{c}_{a.tag}.jsonl")}
        for r in R:
            if r["transaction_id"] in pre:
                r["arms"]["PRECHECK"] = {"decision": pre[r["transaction_id"]]}
            if r["transaction_id"] in avp:
                r["arms"]["AV2+"] = {"decision": avp[r["transaction_id"]]}
        arms = [x for x in ARMS if any(x in r["arms"] for r in R)]
        by = defaultdict(list)
        for r in R:
            by[r["transaction_type"]].append(r)
        eps = defaultdict(set)
        for r in R:
            eps[r["episode_id"]].add(r["transaction_type"])
        md += [f"## 조건 ({c})", "",
               f"- 분모: 거래 {len(R)}(제외 여정 {len(excl)}개 뒤), 대화 {len(eps)}, 정상 거래가 없는 대화 {sum('normal' not in v for v in eps.values())}.", "",
               "| 유형 (n) | " + " | ".join(arms) + " | 기본 권한 대조: 불일치 |", "|---|" + "---|" * len(arms) + "---:|"]
        for tt in TYPES:
            G = by.get(tt, [])
            md.append(f"| {tt} ({len(G)}) | " + " | ".join(acd(G, x) for x in arms) + f" | {sum(bool(r.get('authority_check_codes')) for r in G)} |")
        md += ["", f"### 맥락 위반 필드별 ALLOW (context_only, 조건 {c})", "",
               "| 필드 | n | " + " | ".join(arms) + " |", "|---|---:|" + "---:|" * len(arms)]
        ctx = by.get("context_only", [])
        fields = Counter(f for r in ctx for f in (tg.get(r["transaction_id"], {}).get("context_reasons") or []))
        for f, _ in fields.most_common():
            for lab, G in ((f, [r for r in ctx if f in (tg[r["transaction_id"]].get("context_reasons") or [])]),
                           (f + " 단독", [r for r in ctx if (tg[r["transaction_id"]].get("context_reasons") or []) == [f]])):
                if G:
                    cells = [sum(r["arms"][x]["decision"] == "ALLOW" for r in G if x in r["arms"]) for x in arms]
                    res[f"{c}|ctx|{lab}"] = dict(zip(arms, cells), n=len(G))
                    md.append(f"| {lab} | {len(G)} | " + " | ".join(map(str, cells)) + " |")
        md += ["", f"### 권한 위반 필드별 (authority_only, 조건 {c}): 각 구성의 자체 판정 ALLOW / 기본 권한 대조 불일치", "",
               "| 권한 필드 | n | " + " | ".join(f"{x} ALLOW" for x in arms) + " | 기본 권한 대조 |", "|---|---:|" + "---:|" * len(arms) + "---:|"]
        auth = by.get("authority_only", [])
        af = Counter(f for r in auth for f in (tg.get(r["transaction_id"], {}).get("authority_reasons") or []))
        for f, _ in af.most_common():
            G = [r for r in auth if f in (tg[r["transaction_id"]].get("authority_reasons") or [])]
            md.append(f"| {f} | {len(G)} | " + " | ".join(str(sum(r["arms"][x]["decision"] == "ALLOW" for r in G if x in r["arms"])) for x in arms)
                      + f" | {sum(bool(r.get('authority_check_codes')) for r in G)} |")
        # paired: same cart, authority fine vs authority broken
        key = lambda r: (r["episode_id"], json.dumps(sorted((r["arms"].get("B2") or {}).get("codes") or []), ensure_ascii=False))  # noqa: E731
        md += ["", f"### 같은 장바구니 짝: 권한 정상 대 권한 위반 (조건 {c}, 판정이 다른 짝 수 / 짝 수)", ""]
        for base, broken in (("normal", "authority_only"), ("context_only", "both")):
            pairs = defaultdict(dict)
            for r in by.get(base, []) + by.get(broken, []):
                pairs[r["episode_id"]].setdefault(r["transaction_type"], []).append(r)
            n = 0
            diff = Counter()
            for e, v in pairs.items():
                for x, y in zip(v.get(base, []), v.get(broken, [])):
                    n += 1
                    for arm in arms:
                        if arm in x["arms"] and arm in y["arms"] and x["arms"][arm]["decision"] != y["arms"][arm]["decision"]:
                            diff[arm] += 1
            md.append(f"- {base} ↔ {broken}: 짝 {n}; 판정이 다른 짝 " + ", ".join(f"{arm} {diff[arm]}" for arm in arms))
        md.append("")
    (out_dir / "by_type.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (out_dir / "BY_TYPE.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md[:24]))


if __name__ == "__main__":
    main()
