"""G1v2: state baselines DST-ACC and DST-LATEST (docs/COMPARISON_ARMS_20261126.md) on the stored P3a extraction.

No model calls, no NLI. Scored with the same run_g1v2.score as the four PLAN_v3 arms (stored rows), side by side.
Output: results/g1v2_20261126/DST_BASELINES.md, dst_baselines.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/g1v2", "eval/integrated", "eval/e_m1"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import arms as A  # noqa: E402
import run_g1v2 as G  # noqa: E402
from cdv.pipeline import state_to_entries  # noqa: E402

OUT = ROOT / "results" / "g1v2_20261126"
ARMS = ("plain", "fnctod", "DST-ACC", "DST-LATEST", "fnctod_r", "fnctod_rn")


def main():
    res, md = {}, ["# G1v2 상태 기준선: 단순 누적(DST-ACC), 최신 발화 갱신(DST-LATEST) (P3a 추출 재사용, 모델 호출 0)", "",
                   "| 분할 | 지표 | " + " | ".join(ARMS) + " |", "|---|---|" + "---|" * len(ARMS)]
    for sp in ("eval", "dev"):
        cases = {json.loads(l)["case_id"]: json.loads(l) for l in (G.GEN / f"{sp}.jsonl").read_text(encoding="utf-8").splitlines() if l}
        rows = [json.loads(l) for l in (OUT / f"rows_{sp}.jsonl").read_text(encoding="utf-8").splitlines() if l]
        cnt = Counter()
        for r in rows:
            c = cases[r["case_id"]]
            st = [dict(s, seq=int(s["turn_id"][1:])) for s in r["fnctod_states"]]
            for name, fn in (("DST-ACC", A.dst_acc), ("DST-LATEST", A.dst_latest)):
                steps = [G.vals(state_to_entries(fn(st[:i + 1]))) for i in range(len(st))]
                sc = G.score(c, steps[-1] if steps else {}, steps, False)
                for m in ("final_ok", "steps_ok", "preserved"):
                    if sc[m] is not None:
                        cnt[(name, m, "ok")] += bool(sc[m]); cnt[(name, m, "n")] += 1
            for name in ("plain", "fnctod", "fnctod_r", "fnctod_rn"):
                for m in ("final_ok", "steps_ok", "preserved"):
                    v = r["arms"][name][m]
                    if v is not None:
                        cnt[(name, m, "ok")] += bool(v); cnt[(name, m, "n")] += 1
        res[sp] = {f"{a}|{m}": f"{cnt[(a, m, 'ok')]}/{cnt[(a, m, 'n')]}" for a in ARMS for m in ("final_ok", "steps_ok", "preserved") if cnt[(a, m, "n")]}
        for m, lab in (("final_ok", "최종 정답"), ("steps_ok", "턴별 정답"), ("preserved", "보존")):
            md.append(f"| {sp} | {lab} | " + " | ".join(res[sp].get(f"{a}|{m}", "–") for a in ARMS) + " |")
    (OUT / "dst_baselines.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
    (OUT / "DST_BASELINES.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
