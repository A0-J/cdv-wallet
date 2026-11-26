"""Split-overlap check for the external dataset v3 (no model calls; reads v3 JSONL as data, runs none of its code).

Compares v3 episode_gold.source.episode_id (dev, eval) with: G1v2 dev/eval base journeys (manifest), the exposure
registry, episodes already used here (E-M1 PLAN_v3 rows, P2 validation dev extraction), and finds the CartTrace split
each v3 source journey comes from. There is no sealed final sample yet, so that comparison is reported as absent.
Output: results/v3check_20261126/overlap.json
"""
from __future__ import annotations

import glob
import json
import re
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
V3 = Path(r"C:/Users/user/Documents/Codex/2026-11-26/c-ct/outputs/carttrace_eval_v3")
DATA = Path(r"C:/ct/kit/dataset/data")
OUT = ROOT / "results" / "v3check_20261126"


def ids_in(path: Path) -> set:
    return set(re.findall(r"ep-[0-9a-f]{12}", path.read_text(encoding="utf-8"))) if path.exists() else set()


def main():
    v3 = {}
    for sp in ("dev", "eval"):
        v3[sp] = [json.loads(l)["source"]["episode_id"] for l in (V3 / sp / "episode_gold.jsonl").read_text(encoding="utf-8").splitlines() if l]
    man = json.loads((ROOT / "results" / "g1v2_20261126" / "manifest.json").read_text(encoding="utf-8"))
    others = {
        "G1v2_dev_bases": set(man["splits"]["dev"]["base_episode_ids"]),
        "G1v2_eval_bases": set(man["splits"]["eval"]["base_episode_ids"]),
        "exposure_registry": ids_in(Path(r"C:/agentic-wallet-security/data/derived/test_census_v0_1/exposure_registry.json")),
        "E-M1_PLAN_v3_rows": set().union(*[ids_in(p) for p in (ROOT / "results" / "e_m1_20261126").glob("rows_*.jsonl")]),
        "P2_validation_dev": set().union(*[ids_in(p) for p in (ROOT / "results" / "integrated_dev_20261126").glob("extract_V?.jsonl")]),
    }
    allv3 = set(v3["dev"]) | set(v3["eval"])
    split_of = {}
    for s in ("train", "validation", "test_cross_store", "test_cross_template"):
        for f in glob.glob(str(DATA / "messages" / "*" / f"{s}-*.parquet")):
            for r in pq.read_table(f, columns=["episode_id"], filters=[("episode_id", "in", list(allv3))]).to_pylist():
                split_of[r["episode_id"]] = s
    res = {"note": __doc__.split("\n\n")[0], "sealed_final_sample": "not drawn yet (nothing to compare)",
           "v3": {sp: {"n": len(x), "unique": len(set(x)), "carttrace_split": dict(Counter(split_of.get(e, "NOT_FOUND") for e in x))}
                  for sp, x in v3.items()},
           "v3_dev_vs_eval_overlap": len(set(v3["dev"]) & set(v3["eval"])),
           "overlap": {f"v3_{sp}": {k: sorted(set(x) & s)[:10] + ([f"... total {len(set(x) & s)}"] if len(set(x) & s) > 10 else [])
                                    for k, s in others.items()} for sp, x in v3.items()},
           "overlap_counts": {f"v3_{sp}": {k: len(set(x) & s) for k, s in others.items()} for sp, x in v3.items()}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "overlap.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: res[k] for k in ("v3", "v3_dev_vs_eval_overlap", "overlap_counts")}, indent=1))


if __name__ == "__main__":
    main()
