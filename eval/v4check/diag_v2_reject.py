"""Why does M1 v2 reject candidate changes that v4 labels 'accept'? (v4 dev, no model calls; diagnosis only, no fix)

Follows eval/v3check/inject.py::v2_decide step by step and records which branch produced REJECT:
  NON_USER_CITED        the cited turn is not a user turn
  NON_USER_SOURCE       no user anchor in the cited turn AND the value appears in earlier agent/tool text
  REVOKE_NO_ANCHOR      a removal with no widening cue in the cited turn
  VERIFY_REJECT         anchored, but m1.verify_turn rejected it (codes recorded)
Also: was the value present in an earlier non-user turn (v4 reuses the same sentence for every speaker)?
Output: results/v4check_20261126/diag_v2_reject_dev.json (counts only; no dataset sentences)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/v3check"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import inject as I  # noqa: E402
from cdv import m1  # noqa: E402
from cdv.m1 import ChangeOp, Entry, UserTurn  # noqa: E402
from cdv.v2.m1v2 import anchor_v2, in_non_user_text  # noqa: E402

V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4")


def main():
    from cdv.nli import NLI
    nli = NLI()
    eps = {json.loads(l)["episode_id"]: json.loads(l) for l in (V4 / "dev" / "episodes.jsonl").read_text(encoding="utf-8").splitlines() if l}
    gold = {json.loads(l)["episode_id"]: json.loads(l) for l in (V4 / "dev" / "episode_gold.jsonl").read_text(encoding="utf-8").splitlines() if l}
    why = Counter()
    for e, ep in eps.items():
        g = gold[e]
        cat = {c["sku"]: c for c in ep["catalog"]}
        turns = [dict(x, idx=i) for i, x in enumerate(ep["dialogue"])]
        users = {x["turn_id"]: UserTurn(x["turn_id"], x["idx"], x["text"]) for x in turns if x["role"] == "user"}
        prev = I.prior_ledger(g["initial_state"], cat)
        for op in ep["candidate_operations"]:
            if g["operation_labels"].get(op["op_id"]) != "accept" or op["field"] == "Attribute":
                continue
            if I.v2_decide(prev, op, cat, turns, users, nli) != "REJECT":
                continue
            t = op["evidence_turn_id"]
            key = (op["operation"], op["field"])
            if t not in users:
                why[key + ("NON_USER_CITED",)] += 1
                continue
            before = [x["text"] for x in turns if x["role"] != "user" and x["idx"] < users[t].seq]
            if op["field"] == "Product":
                why[key + ("PRODUCT_PATH",)] += 1
                continue
            for eid, en in I.entries_from(op["field"], op["value"], cat, basis=(t,)):
                p = prev.by_id().get(eid)
                if en is None and p is None:
                    continue
                o = "revoke" if en is None else (I.OPMAP[op["operation"]] if p is not None or op["operation"] != "OVERRIDE" else "add")
                cited, how = anchor_v2(en, o, [users[t]], nli)
                if not cited:
                    if o == "revoke":
                        why[key + ("REVOKE_NO_ANCHOR",)] += 1
                    elif en is not None and in_non_user_text(en, before):
                        why[key + ("NON_USER_SOURCE (value said earlier by agent/tool)",)] += 1
                    else:
                        why[key + ("NOT_FOUND->would be CLARIFY",)] += 1
                    continue
                res = m1.verify_turn(prev, [ChangeOp(o, eid, en if en is None else Entry(en.id, en.field, en.value, en.strength, cited, en.scope), cited)],
                                     list(users.values()))
                f = res.change_findings[0]
                if f.status == m1.REJECT:
                    why[key + ("VERIFY_REJECT " + ",".join(f.codes),)] += 1
    out = {"split": "dev", "accept_labelled_ops_rejected_by_v2": sum(why.values()),
           "by_cause": [{"operation": k[0], "field": k[1], "cause": k[2], "n": v} for k, v in why.most_common()]}
    dst = ROOT / "results" / "v4check_20261126" / "diag_v2_reject_dev.json"
    dst.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
