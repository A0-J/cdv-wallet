"""Compute the auxiliary B3-A next to B3 (no model calls: M1-G answers replayed from the run's ledger).

For each transaction / matched challenge of rows_{name}_{split}_{cond}_{tag}.jsonl:
  B3 (replay)  frozen path with the replayed answers   (equals the stored B3 when each request has one answer)
  B3-A         the asymmetric-rejection mirror           (eval/aux_arms/b3a.py)
Reports: tables by transaction type (B2, B3 stored, B3 replay, B3-A, PRECHECK), false-premise consent (matched case 4)
ALLOW/CLARIFY/DENY, the B3-vs-B2 normal-allow gap and the B3 context-violation allows broken down by cause, and the
same breakdown for B3-A. Replay misses are counted (never sent).
Usage: .venv/Scripts/python.exe eval/aux_arms/run_b3a.py --data <root> --name v4 --split dev --tag m1g --m1g-ledger v4 [--cond A]
Output: results/review_20261127/b3a_{name}_{split}/{B3A_<cond>.md, b3a_rows_<cond>.jsonl}
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check", "eval/extdata", "eval/review", "eval/aux_arms"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import run_ext as RX  # noqa: E402
from b3a import b3_like  # noqa: E402
from paired_compare import component  # noqa: E402
from replay import Replay  # noqa: E402

X = ROOT / "results" / "extdata_20261126"


def jl(p):
    p = Path(p)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def acd(G, arm):
    c = Counter(r["arms"][arm]["decision"] for r in G if arm in r["arms"])
    return f"{c['ALLOW']}/{c['CLARIFY']}/{c['DENY']}"


def cause(a):
    c = component(a.get("codes"), a.get("m1_asks"))
    kinds = sorted(set(a.get("unresolved_kinds") or [])) if a.get("m1_asks") else []
    return c + (f" [{','.join(kinds)}]" if kinds else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--tag", default="m1g")
    ap.add_argument("--m1g-ledger", required=True, help="label of ledger_m1g_<label>.jsonl to replay")
    ap.add_argument("--cond", default="A")
    a = ap.parse_args()
    d = Path(a.data) / a.split
    eps = {e["episode_id"]: e for e in jl(d / "episodes.jsonl")}
    txs = {t["transaction_id"]: t for t in jl(d / "transactions.jsonl")}
    mx = {m["challenge_id"]: m for m in jl(d / "matched_stockout.jsonl")}
    tg = {g["transaction_id"]: g for g in jl(d / "transaction_gold.jsonl")}
    rows = jl(X / f"rows_{a.name}_{a.split}_{a.cond}_{a.tag}.jsonl")
    mrows = jl(X / f"rows_{a.name}_{a.split}_{a.cond}_{a.tag}_matched.jsonl")
    pre = {x["id"]: x["precheck"] for x in jl(X / (f"baselines_{a.name}_{a.split}.jsonl" if a.cond == "A" else f"baselines_{a.name}_{a.split}_B.jsonl"))}
    llm = Replay(X / f"ledger_m1g_{a.m1g_ledger}.jsonl")
    by_ep = {r["episode_id"]: r for r in rows}
    out, missed = [], 0
    for kind, R in (("tx", rows), ("matched", mrows)):
        for r in R:
            src = r if kind == "tx" else by_ep.get(r["episode_id"])
            if src is None:
                continue
            tx = txs[r["transaction_id"]] if kind == "tx" else mx[r["challenge_id"]]
            case = RX.build_case(eps[r["episode_id"]], tx, (tg.get(r.get("transaction_id")) or {}) if kind == "tx" else {})
            states = [{"turn_id": s["turn_id"], "state": s["state"]} for s in src["fnctod_states"]]
            m0 = llm.misses
            try:
                b3r = b3_like(case, states, llm, asym=False)
                b3a = b3_like(case, states, llm, asym=True)
            except RuntimeError:
                missed += 1
                continue
            if llm.misses > m0:
                missed += 1
                continue
            r["arms"]["B3_replay"], r["arms"]["B3-A"] = b3r, b3a
            uid = r.get("transaction_id") or r.get("challenge_id")
            if uid in pre:
                r["arms"]["PRECHECK"] = {"decision": pre[uid]}
            out.append({"kind": kind, "id": uid, "B3_replay": b3r["decision"], "B3-A": b3a["decision"],
                        "B3-A_codes": b3a["codes"], "B3-A_unresolved": b3a["unresolved_kinds"]})
    od = ROOT / "results" / "review_20261127" / f"b3a_{a.name}_{a.split}"
    od.mkdir(parents=True, exist_ok=True)
    (od / f"b3a_rows_{a.cond}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out), encoding="utf-8", newline="\n")
    ok = [r for r in rows if "B3-A" in r["arms"]]
    same = sum(r["arms"]["B3"]["decision"] == r["arms"]["B3_replay"]["decision"] for r in ok)
    arms = ["B2", "B3", "B3_replay", "B3-A", "PRECHECK"]
    md = [f"# B3-A(비대칭 기각, 보조 구성, Holm 대상 아님) — {a.name} {a.split} 조건 {a.cond}, 모델 호출 0", "",
          f"- M1-G 응답은 `ledger_m1g_{a.m1g_ledger}.jsonl` 재생. 원장에 없는 요청 때문에 계산하지 못한 거래 {missed}(보내지 않음), 재생 적중 {llm.hits}, 미스 {llm.misses}.",
          f"- 저장된 B3 대 재생한 B3 판정 일치 {same}/{len(ok)} (원장에 같은 요청의 답이 여럿이면 재생은 하나만 쓴다).", "",
          "| 유형 (n) | " + " | ".join(arms) + " |", "|---|" + "---|" * len(arms)]
    for tt in ("normal", "context_only", "both", "authority_only"):
        G = [r for r in ok if r["transaction_type"] == tt]
        md.append(f"| {tt} ({len(G)}) | " + " | ".join(acd(G, x) for x in arms) + " |")
    M4 = [m for m in mrows if m.get("intent_case") == 4 and "B3-A" in m["arms"]]
    md += ["", f"## 거짓 전제 동의 (매칭 사례 4, n={len(M4)}, 기준 판정 CLARIFY; DENY는 정답 아님)", "",
           "| 구성 | ALLOW | CLARIFY | DENY |", "|---|---:|---:|---:|"]
    for x in arms:
        c = Counter(m["arms"][x]["decision"] for m in M4 if x in m["arms"])
        md.append(f"| {x} | {c['ALLOW']} | {c['CLARIFY']} | {c['DENY']} |")
    for lab, tt, base, arm, cond_fn in (
            ("B3가 B2보다 정상 거래를 덜 허용한 거래 (B2 ALLOW, B3 아님)", "normal", "B2", "B3_replay", lambda b, x: b == "ALLOW" and x != "ALLOW"),
            ("B3-A가 B2보다 정상 거래를 덜 허용한 거래", "normal", "B2", "B3-A", lambda b, x: b == "ALLOW" and x != "ALLOW"),
            ("B3가 B2보다 위반 거래를 더 허용한 거래 (B2 차단, B3 ALLOW)", "context_only", "B2", "B3_replay", lambda b, x: b != "ALLOW" and x == "ALLOW"),
            ("B3-A가 B2보다 위반 거래를 더 허용한 거래", "context_only", "B2", "B3-A", lambda b, x: b != "ALLOW" and x == "ALLOW")):
        G = [r for r in ok if r["transaction_type"] == tt and cond_fn(r["arms"][base]["decision"], r["arms"][arm]["decision"])]
        md += ["", f"## {lab}: {len(G)}건", ""]
        if tt == "normal":
            md.append("- " + arm + " 판정·원인: " + ", ".join(f"{k} {v}" for k, v in Counter(
                f"{r['arms'][arm]['decision']}: {cause(r['arms'][arm])}" for r in G).most_common()))
        else:
            md.append("- 정답 위반 필드: " + ", ".join(f"{k} {v}" for k, v in Counter(
                f for r in G for f in tg[r['transaction_id']].get('context_reasons') or []).most_common()))
            md.append("- B2 차단 사유: " + ", ".join(f"{k} {v}" for k, v in Counter(
                str(c).split(':')[0] for r in G for c in r['arms']['B2']['codes'] if c != 'OUT_OF_SCOPE').most_common()))
            md.append("- M1 기각 코드(B3): " + ", ".join(f"{k} {v}" for k, v in Counter(c for r in G for (_, c) in r['m1']['rejected']).most_common()))
    (od / f"B3A_{a.cond}.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
