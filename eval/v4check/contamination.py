"""v4 dev contamination-injection condition (no model calls; M1-G decisions reused from the approved M1-G run 1).

Prior state: episode_gold.initial_state (oracle prior of the intervention path). candidate_operations are applied in
evidence-turn order. Same transactions, same real gate (eval/integrated/arms.py Env.full_gate) for every arm.
  M2 Only          every candidate operation applied (an unverified extractor would have proposed them)
  M1+M2 [X]        X in {v1, v2, M1-G}: operations X accepts are applied; X 'reject' -> not applied;
                   X 'clarify' -> unresolved: B3-type = ask only if some combination of those ops changes the gate
                   decision (all combinations), B4-type = ask whenever one exists
  Oracle           gold effective_state (reported apart)
Main number: on transactions with transaction_gold.follows_rejected_proposal, how many each arm ALLOWs (unjustified).
Also expected-allow transactions (false blocks). Exclusion: the same 2 episodes as P4 (exclusion_v4_dev.json).
Output: results/v4check_20261126/contamination_dev.json, CONTAMINATION_dev.md
"""
from __future__ import annotations

import copy
import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check", "eval/extdata"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import arms as A  # noqa: E402
import inject as I  # noqa: E402
import run_ext as X  # noqa: E402
from cdv import verdict  # noqa: E402
from cdv.m1 import UserTurn  # noqa: E402
from cdv.v2.integrate import ledger_to_mandate  # noqa: E402

V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4")
OUT = ROOT / "results" / "v4check_20261126"
MAX_COMBO_OPS = 6


def apply(state: dict, op: dict) -> dict:
    s = copy.deepcopy(state)
    f, o, v = op["field"], op["operation"], op.get("value")
    if o == "REVOKE" or v in (None, {}, []):
        s.pop(f, None)
    elif f == "Substitution":
        s["Substitution"] = {**(s.get("Substitution") or {}), **v}
    else:
        s[f] = v
    return s


def gate(env, case, cat, state):
    m = ledger_to_mandate(X.gold_ctx({"effective_state": state}, cat), case.reg, case.seller, f"m-{case.episode_id}", 1, env.session)
    return env.full_gate(m)


def main(tag="", data=None, name="v4", split="dev", m1g_rows_file=None, out=None):
    """Defaults = the dev run (v4 dev, M1-G rows of the prompt-v1 run 1). Harness options added 2026-11-27 after the
    policy freeze: data / name / split / m1g_rows_file / out for the v4b eval (decision code unchanged)."""
    global OUT
    OUT = out or OUT
    data = data or V4
    sfx = f"_{tag}" if tag else ""
    eps = {e["episode_id"]: e for e in X.jl(data / split / "episodes.jsonl")}
    eg = {g["episode_id"]: g for g in X.jl(data / split / "episode_gold.jsonl")}
    tg = {g["transaction_id"]: g for g in X.jl(data / split / "transaction_gold.jsonl")}
    excl = set(json.loads((ROOT / "results" / "extdata_20261126" / f"exclusion_{name}_{split}.json").read_text(encoding="utf-8"))["excluded_episodes"])
    m1g_rows = [json.loads(l) for l in (m1g_rows_file or ROOT / "results" / "m1g_20261126" / "rows_dev.jsonl").read_text(encoding="utf-8").splitlines() if l]
    # M1-G rows are in the same order as episodes.jsonl x candidate_operations (inject_m1g.py)
    it = iter(m1g_rows)
    m1g = {}
    for e, ep in eps.items():
        for k, op in enumerate(ep["candidate_operations"]):
            r = next(it)
            assert r["episode_id"] == e and r["field"] == op["field"] and r["op"] == op["operation"], "M1-G row order mismatch"
            m1g[(e, k)] = r["m1g_run1"]
    from cdv.nli import NLI
    nli = NLI()
    decisions = {}
    for e, ep in eps.items():
        if e in excl:
            continue
        cat = {c["sku"]: c for c in ep["catalog"]}
        turns = [dict(x, idx=i) for i, x in enumerate(ep["dialogue"])]
        users = {x["turn_id"]: UserTurn(x["turn_id"], x["idx"], x["text"]) for x in turns if x["role"] == "user"}
        prev = I.prior_ledger(eg[e]["initial_state"], cat)
        order = {x["turn_id"]: x["idx"] for x in turns}
        ops = sorted(enumerate(ep["candidate_operations"]), key=lambda kv: order.get(kv[1]["evidence_turn_id"], 0))
        decisions[e] = [(op, {"v1": I.v1_decide(prev, op, cat, turns, users),
                              "v2": I.v2_decide(prev, op, cat, turns, users, nli), "M1-G": m1g[(e, k)]}) for k, op in ops]
    tab = defaultdict(Counter)
    approx = Counter()
    per_tx = []                                       # per-transaction decisions (harness addition 2026-11-27)
    for tx in X.jl(data / split / "transactions.jsonl"):
        e = tx["episode_id"]
        if e in excl:
            continue
        ep, g, gt = eps[e], eg[e], tg.get(tx["transaction_id"]) or {}
        cat = {c["sku"]: c for c in ep["catalog"]}
        case = X.build_case(ep, tx, gt)
        env = A.Env(case)
        init = g["initial_state"]
        groups = ["all"] + (["follows_rejected_proposal"] if gt.get("follows_rejected_proposal") else []) + \
                 [f"expected_{gt.get('expected_checkout')}", f"type_{gt.get('transaction_type')}"]
        res = {}
        st = init
        for op, _ in decisions[e]:
            st = apply(st, op)
        d, c = gate(env, case, cat, st)
        res["M2 Only (all ops)"] = verdict.integrated(d, c, False)
        d, c = gate(env, case, cat, g["effective_state"])
        res["Oracle"] = verdict.integrated(d, c, False)
        for v in ("v1", "v2", "M1-G"):
            st = init
            pend = []
            for op, dec in decisions[e]:
                if dec[v] == "ACCEPT":
                    st = apply(st, op)
                elif dec[v] == "CLARIFY":
                    pend.append(op)
            d0, c0 = gate(env, case, cat, st)
            res[f"M1+M2 [{v}] B4-type"] = verdict.integrated(d0, c0, bool(pend))
            if not pend:
                res[f"M1+M2 [{v}] B3-type"] = verdict.integrated(d0, c0, False)
                continue
            use = pend[:MAX_COMBO_OPS]
            approx[v] += len(pend) > MAX_COMBO_OPS
            outs = set()
            for mask in itertools.product((0, 1), repeat=len(use)):
                s2 = st
                for on, op in zip(mask, use):
                    if on:
                        s2 = apply(s2, op)
                outs.add(gate(env, case, cat, s2)[0])
            res[f"M1+M2 [{v}] B3-type"] = "CLARIFY" if len(outs) > 1 else verdict.integrated(d0, c0, False)
        per_tx.append({"transaction_id": tx["transaction_id"], "episode_id": e, "groups": groups, "decisions": res})
        for grp in groups:
            for arm, dec in res.items():
                tab[(grp, arm)][dec] += 1
    arms = sorted({a for _, a in tab})
    out = {"excluded_episodes": sorted(excl), "approx_cases": dict(approx),
           "table": {f"{g}|{a}": dict(v) for (g, a), v in sorted(tab.items())}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"contamination_{split}{sfx}.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    (OUT / f"contamination_{split}{sfx}_rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in per_tx),
                                                               encoding="utf-8", newline="\n")
    md = ["# v4 dev 오염 주입 조건 (모델 호출 0; M1-G는 승인된 1회차 판정 재사용)", "",
          "- 이전 상태 = 정답 initial_state(주입 경로 오라클), 후보 연산을 근거 턴 순서로 적용. 같은 거래·같은 게이트. 생성 데이터.",
          "- 권한(grant) 축은 이 게이트의 검사 대상이 아니다(별도 축). 유형별 표에서 authority_only는 참고로만 본다.",
          f"- 제외 여정 {len(excl)}. 확인 연산이 {MAX_COMBO_OPS}개를 넘어 조합을 잘라 본 거래: {dict(approx)}.", ""]
    for grp in ("follows_rejected_proposal", "type_normal", "type_context_only", "type_both", "type_authority_only",
                "expected_allow", "expected_block", "all"):
        rows = [(a, tab[(grp, a)]) for a in arms if tab[(grp, a)]]
        if not rows:
            continue
        n = sum(rows[0][1].values())
        md += [f"## {grp} (n={n})", "", "| 비교군 | ALLOW | CLARIFY | DENY |", "|---|---:|---:|---:|"]
        md += [f"| {a} | {c.get('ALLOW', 0)} | {c.get('CLARIFY', 0)} | {c.get('DENY', 0)} |" for a, c in rows]
        md.append("")
    (OUT / f"CONTAMINATION_{split}{sfx}.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("tag", nargs="?", default="")
    ap.add_argument("--data", type=Path, default=None)
    ap.add_argument("--name", default="v4")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--m1g-rows", type=Path, default=None, help="inject_m1g rows file whose m1g_run1 is used")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    if a.out and any(a.out.glob(f"contamination_{a.split}{('_' + a.tag) if a.tag else ''}.json")):
        raise SystemExit("refusing to overwrite")
    main(a.tag, a.data, a.name, a.split, a.m1g_rows, a.out)
