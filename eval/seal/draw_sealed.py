"""Draw and seal the final-evaluation sample now (2026-11-26). No model calls. IDs only.

Composition (docs/INTEGRATED_EVAL_DESIGN.md section 8, M1 development never used these splits/journeys):
  S_R1  300  R1-type (baseline, a stated non-substitute condition, cart present) from test_cross_template
  S_R3  100  R3-type (baseline with a stockout fault, cart present) from train (test_cross_template has no stockouts)
Excluded before drawing (already seen): exposure registry, E-M1 PLAN_v3 rows, P2 validation dev extraction,
  G1v2 dev/eval base journeys, every source journey of the external datasets v2/v3g, G1 dev/eval base journeys.
Selection reuses eval/e_m1/run.py::select (same rule as PLAN_v3) with a new seed.
Output: results/sealed_20261126/sealed_ids.json (+ its sha256 printed); from now on every development script
must exclude these IDs (helper: load_sealed()).
"""
from __future__ import annotations

import glob
import hashlib
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "e_m1"))
import run as R  # noqa: E402

OUT = ROOT / "results" / "sealed_20261126"
SEED = 20261130
EXTERNAL = [Path(r"C:/Users/user/Documents/Codex/2026-11-26/c-ct/outputs/carttrace_eval_v3"),
            Path(r"C:/Users/user/Documents/Codex/2026-11-26/c-ct/outputs/carttrace_eval_v2")]


def ids_in_text(p: Path) -> set:
    return set(re.findall(r"ep-[0-9a-f]{12}", p.read_text(encoding="utf-8", errors="ignore"))) if p.exists() else set()


def seen_ids() -> dict:
    s = {"exposure_registry": ids_in_text(Path(r"C:/agentic-wallet-security/data/derived/test_census_v0_1/exposure_registry.json")),
         "E-M1_rows": set().union(*[ids_in_text(p) for p in (ROOT / "results" / "e_m1_20261126").glob("rows_*.jsonl")]),
         "P2_dev": set().union(*[ids_in_text(p) for p in (ROOT / "results" / "integrated_dev_20261126").glob("extract_V?.jsonl")]),
         "G1v2_bases": set(), "G1_bases": set(), "external_v2_v3g": set()}
    man = json.loads((ROOT / "results" / "g1v2_20261126" / "manifest.json").read_text(encoding="utf-8"))
    for sp in man["splits"].values():
        s["G1v2_bases"] |= set(sp["base_episode_ids"])
    for f in ("dev.jsonl", "eval.jsonl"):
        s["G1_bases"] |= ids_in_text(Path(r"C:/ct/runs/cdv_wallet/generated/G1") / f)
    for d in EXTERNAL:
        for f in glob.glob(str(d / "*" / "*gold*.jsonl")):
            s["external_v2_v3g"] |= ids_in_text(Path(f))
    return s


def load_sealed() -> set:
    d = json.loads((OUT / "sealed_ids.json").read_text(encoding="utf-8"))
    return set(d["S_R1"]) | set(d["S_R3"])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / "sealed_ids.json").exists(), "already sealed; never redraw"
    seen = seen_ids()
    excl = set().union(*seen.values())
    rows_t = [r for r in R.load_messages(["test_cross_template"]) if r["episode_id"] not in excl]
    rows_tr = [r for r in R.load_messages(["train"]) if r["episode_id"] not in excl]
    R.SEED = SEED
    s1 = sorted(r["episode_id"] for r in R.select("R1", "test_cross_template", 300, rows_t))
    s3 = sorted(r["episode_id"] for r in R.select("R3", "train", 100, rows_tr))
    assert len(s1) == 300 and len(s3) == 100 and not (set(s1) & set(s3))
    body = {"seed": SEED, "S_R1": s1, "S_R3": s3,
            "excluded_counts": {k: len(v) for k, v in seen.items()}, "excluded_total": len(excl),
            "rule": "eval/e_m1/run.py::select (PLAN_v3 rule), seen journeys removed first"}
    text = json.dumps(body, indent=2) + "\n"
    (OUT / "sealed_ids.json").write_text(text, encoding="utf-8", newline="\n")
    ids_sha = hashlib.sha256(("\n".join(s1 + s3)).encode()).hexdigest()
    (OUT / "SEALED.md").write_text(
        "# 봉인 표본 (2026-11-26)\n\n"
        f"- 파일 `sealed_ids.json` sha256 `{hashlib.sha256(text.encode()).hexdigest()}`\n"
        f"- ID 목록(S_R1 300 + S_R3 100, 정렬, 줄바꿈 결합) sha256 `{ids_sha}`\n"
        f"- 제외한 이미 본 여정: {json.dumps(body['excluded_counts'])}, 합계 {len(excl)}\n"
        "- 규칙: PLAN_v3 선택 규칙(`run.py::select`), 시드 20261130. 이 ID는 모든 개발 작업에서 제외한다. 결과·대화 내용은 최종 평가 승인 전까지 열지 않는다.\n",
        encoding="utf-8", newline="\n")
    print(json.dumps({"file_sha256": hashlib.sha256(text.encode()).hexdigest(), "ids_sha256": ids_sha,
                      "excluded": body["excluded_counts"], "n": [len(s1), len(s3)]}, indent=1))


if __name__ == "__main__":
    main()
