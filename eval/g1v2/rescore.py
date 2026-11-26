"""Re-score stored G1v2 rows with the CURRENT rules (no model calls) and put them next to the stored scores.

Used after the money-expression rule change (spec MONEY-1, cdv/m1.py sha256 recorded in the output).
Old scores = rows_{split}.jsonl as produced by P3a (PLAN_v3 rules). New scores = run_g1v2.evaluate on the same
stored extractor states. Output: results/g1v2_20261126/rescore_{tag}.json, RESCORE_{tag}.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "g1v2"))
import run_g1v2 as G  # noqa: E402

OUT = ROOT / "results" / "g1v2_20261126"
ARMS = ("plain", "fnctod", "fnctod_r", "fnctod_rn")
METS = ("final_ok", "steps_ok", "preserved", "asked", "unnecessary_question")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    from cdv.nli import NLI
    nli = NLI()
    res = {"m1_sha256": hashlib.sha256((ROOT / "cdv" / "m1.py").read_bytes()).hexdigest(), "splits": {}}
    md = [f"# G1v2 재채점: 규칙 변경 전(P3a) 대 후 ({a.tag})", "",
          f"- 같은 추출 상태, 모델 호출 0. 후 = cdv/m1.py sha256 `{res['m1_sha256']}`.", "",
          "| 분할 | 구성 | 지표 | 전 | 후 | 바뀐 사례 |", "|---|---|---|---:|---:|---:|"]
    for sp in ("eval", "dev"):
        cases = {json.loads(l)["case_id"]: json.loads(l) for l in (G.GEN / f"{sp}.jsonl").read_text(encoding="utf-8").splitlines() if l}
        rows = [json.loads(l) for l in (OUT / f"rows_{sp}.jsonl").read_text(encoding="utf-8").splitlines() if l]
        cnt = Counter()
        for r in rows:
            fn = [dict(s, cost_usd=0.0) for s in r["fnctod_states"]]
            new = G.evaluate(cases[r["case_id"]], fn, {"state": r["plain_state"]}, nli)
            for arm in ARMS:
                for m in METS:
                    o, n = r["arms"][arm][m], new[arm][m]
                    if o is None and n is None:
                        continue
                    cnt[(arm, m, "old")] += bool(o)
                    cnt[(arm, m, "new")] += bool(n)
                    cnt[(arm, m, "n")] += 1
                    cnt[(arm, m, "changed")] += bool(o) != bool(n)
        res["splits"][sp] = {f"{arm}|{m}": {"old": cnt[(arm, m, 'old')], "new": cnt[(arm, m, 'new')], "n": cnt[(arm, m, 'n')],
                                            "changed": cnt[(arm, m, 'changed')]} for arm in ARMS for m in METS if cnt[(arm, m, 'n')]}
        for k, v in res["splits"][sp].items():
            arm, m = k.split("|")
            md.append(f"| {sp} | {arm} | {m} | {v['old']}/{v['n']} | {v['new']}/{v['n']} | {v['changed']} |")
    (OUT / f"rescore_{a.tag}.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
    (OUT / f"RESCORE_{a.tag}.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
