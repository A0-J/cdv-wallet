"""v3g dev vs eval: do follow-up user utterances reuse the same wording? (no model calls; v3g read as data)

Masking: catalog titles, brands and product types of the episode -> <E>; numbers (with separators/decimals) -> <N>;
whitespace and case normalised. Unit: follow-up user utterances (every user turn after the first).
Reports the share of eval utterances (and of distinct eval templates) whose masked form also occurs in dev.
Output: results/v3check_20261126/phrase_overlap.json
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

V3 = Path(r"C:/Users/user/Documents/Codex/2026-11-26/c-ct/outputs/carttrace_eval_v3")
OUT = Path(__file__).resolve().parents[2] / "results" / "v3check_20261126"
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def mask(text, ents):
    t = text
    for e in sorted(ents, key=len, reverse=True):
        if len(e) >= 3:
            t = re.sub(re.escape(e), "<E>", t, flags=re.I)
    t = NUM.sub("<N>", t)
    return " ".join(t.lower().split())


def templates(split):
    out = []
    gold = {json.loads(l)["episode_id"]: json.loads(l) for l in (V3 / split / "episode_gold.jsonl").read_text(encoding="utf-8").splitlines() if l}
    for l in (V3 / split / "episodes.jsonl").read_text(encoding="utf-8").splitlines():
        ep = json.loads(l)
        ents = {x for c in ep["catalog"] for x in (c.get("title"), c.get("brand"), c.get("product_type")) if x}
        users = [t for t in ep["dialogue"] if t["role"] == "user"][1:]
        g = gold[ep["episode_id"]]
        out += [(f"{g['group']}/{g['subtype']}", mask(t["text"], ents)) for t in users]
    return out


def main():
    dev, ev = templates("dev"), templates("eval")
    dset = {m for _, m in dev}
    by = Counter()
    for grp, m in ev:
        by[(grp, m in dset)] += 1
    distinct_eval = {m for _, m in ev}
    res = {"follow_up_utterances": {"dev": len(dev), "eval": len(ev)},
           "distinct_templates": {"dev": len(dset), "eval": len(distinct_eval)},
           "eval_utterances_whose_template_is_in_dev_pct": round(100 * sum(1 for _, m in ev if m in dset) / len(ev), 1),
           "distinct_eval_templates_in_dev_pct": round(100 * len(distinct_eval & dset) / len(distinct_eval), 1),
           "by_type_pct_in_dev": {g: round(100 * by[(g, True)] / (by[(g, True)] + by[(g, False)]), 1)
                                  for g in sorted({g for g, _ in ev})},
           }   # eval sentences are not printed or stored (2026-11-26)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "phrase_overlap.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
