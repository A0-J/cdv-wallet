"""Exploratory zero-call arm 'PRECHECK AND M2': final = the more restrictive of PRECHECK and the gate arm
(DENY > CLARIFY > ALLOW), i.e. pay only if both allow. v4 dev, conditions A and B, transactions + matched.
Output: results/review_20261127/e2_parity/conjunction.json"""
import json
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
RES = ROOT / "results" / "extdata_20261126"
OUT = ROOT / "results" / "review_20261127" / "e2_parity"
V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4/dev")
RANK = {"ALLOW": 0, "CLARIFY": 1, "DENY": 2}
def jl(p): return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
tg = {g["transaction_id"]: g for g in jl(V4 / "transaction_gold.jsonl")}
res = {}
for cond, bf in (("A", "baselines_v4_dev.jsonl"), ("B", "baselines_v4_dev_B.jsonl")):
    pre = {b["id"]: b["precheck"] for b in jl(RES / bf)}
    t = defaultdict(lambda: defaultdict(Counter))
    for r in jl(RES / f"rows_v4_dev_{cond}.jsonl"):
        key = r["transaction_type"] + ("/follows_rejected" if (tg.get(r["transaction_id"]) or {}).get("follows_rejected_proposal") else "")
        p = pre[r["transaction_id"]]
        for arm in ("B2", "B3"):
            d = r["arms"][arm]["decision"]
            t[key][f"PRECHECK&{arm}"][max(p, d, key=RANK.get)] += 1
    for m in jl(RES / f"rows_v4_dev_{cond}_matched.jsonl"):
        key = f"matched case{m['intent_case']} ({m['reference_verdict']})"
        p = pre[m["challenge_id"]]
        for arm in ("B2", "B3"):
            t[key][f"PRECHECK&{arm}"][max(p, m["arms"][arm]["decision"], key=RANK.get)] += 1
    res[cond] = {k: {a: dict(c) for a, c in v.items()} for k, v in sorted(t.items())}
(OUT / "conjunction.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
f = lambda c: f"{c.get('ALLOW',0)}/{c.get('CLARIFY',0)}/{c.get('DENY',0)}"
for cond in res:
    print("==", cond)
    for k, v in res[cond].items():
        print(f"{k:36s}", " | ".join(f"{a}:{f(c)}" for a, c in v.items()))
