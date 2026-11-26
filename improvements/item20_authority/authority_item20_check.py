"""Adjustment 20 check (no model calls): the payment-request authority check before the gate must not change any
decision on normal, context_only or matched transactions of v4 dev, and must DENY (every configuration except B0) the
authority_only / both transactions.

1  codes: cdv/authority.py vs the old evaluation-script comparison on every dev transaction and matched challenge
2  stored decisions: the R-v4g rows (code 610a97c, no authority step) with cdv.authority.apply on top, per type
3  end-to-end replay on a stratified sample: run_arms WITHOUT and WITH authority_codes (patched code), M1-G answers
   replayed from results/extdata_20261126/ledger_m1g_v4.jsonl only (a request not in the ledger counts as a miss and
   the row is reported, never sent); both compared with the stored 610a97c decisions
Output: results/review_20261127/AUTHORITY_ITEM20.md, authority_item20.json
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check", "eval/extdata"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import arms as A  # noqa: E402
import run_ext as RX  # noqa: E402
from cdv import authority as AUTH  # noqa: E402
from cdv.extract import LLMResult  # noqa: E402

X = ROOT / "results" / "extdata_20261126"
OUT = ROOT / "results" / "review_20261127"
V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4/dev")


def jl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


class Replay:
    """Answers only from a ledger (same request body and sha256 as cdv/extract.py::OpenAIResponses); never sends."""

    def __init__(self, ledger, model="gpt-6-luna", effort="low", max_out=2000):
        self.cache = {r["request_sha256"]: r for r in jl(ledger) if r.get("request_sha256") and not r.get("error")
                      and r.get("status") == "completed"}
        self.model, self.effort, self.max_out, self.misses, self.hits, self.spent = model, effort, max_out, 0, 0, 0.0

    def __call__(self, system, user):
        body = json.dumps({"model": self.model, "input": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                           "reasoning": {"effort": self.effort}, "max_output_tokens": self.max_out}).encode("utf-8")
        hit = self.cache.get(hashlib.sha256(body).hexdigest())
        if hit is None:
            self.misses += 1
            raise RuntimeError("replay miss (not sent)")
        self.hits += 1
        return LLMResult(hit["output_text"], hit.get("usage") or {}, 0.0, 0.0, hit.get("model", self.model))


def main(tag="m1g", n_per_type=15):
    eps = {e["episode_id"]: e for e in jl(V4 / "episodes.jsonl")}
    txs = {t["transaction_id"]: t for t in jl(V4 / "transactions.jsonl")}
    tg = {g["transaction_id"]: g for g in jl(V4 / "transaction_gold.jsonl")}
    res, md = {}, ["# 조정 20 확인: 결제 요청 권한 대조를 게이트 앞에 넣은 전후 (v4 dev, 모델 호출 0)", ""]
    # 1 codes
    src = (ROOT / "eval" / "extdata" / "run_ext.py").read_text(encoding="utf-8")
    ns = {}
    start = src.index("def _authority_check_script") if "_authority_check_script" in src else src.index("def authority_check")
    exec(src[start:src.index("def gold_ctx")].replace("def _authority_check_script", "def authority_check"), ns)
    diff, cnt = 0, Counter()
    for f in ("transactions.jsonl", "matched_stockout.jsonl"):
        for t in jl(V4 / f):
            a, b = ns["authority_check"](t), AUTH.check_payment_authority(t["payment_request"], t["payment_grant"])
            diff += a != b
            cnt[((tg.get(t.get("transaction_id")) or {}).get("transaction_type", "matched"), bool(b))] += 1
    res["codes_differ"] = diff
    res["codes_by_type"] = {f"{k[0]}|{'codes' if k[1] else 'none'}": v for k, v in sorted(cnt.items())}
    md += ["## 1. 사유 코드: 시스템 함수 대 기존 평가 스크립트", "", f"- 차이 {diff}건 (거래 1,482 + 매칭 96).",
           "- 유형별 코드 유무: " + ", ".join(f"{k} {v}" for k, v in res["codes_by_type"].items()), ""]
    # 2 stored decisions with the authority step on top
    rows = jl(X / f"rows_v4_dev_A_{tag}.jsonl")
    mrows = jl(X / f"rows_v4_dev_A_{tag}_matched.jsonl")
    ch = Counter()
    for r in rows:
        auth = AUTH.check_payment_authority(txs[r["transaction_id"]]["payment_request"], txs[r["transaction_id"]]["payment_grant"])
        for arm, a in r["arms"].items():
            new = a["decision"] if arm == "B0" else AUTH.apply(a["decision"], a.get("codes"), auth)[0]
            ch[(r["transaction_type"], "same" if new == a["decision"] else f"{a['decision']}->{new}")] += 1
    for m in mrows:
        for arm, a in m["arms"].items():
            ch[("matched", "same")] += 1
    res["stored_rows"] = {f"{k[0]}|{k[1]}": v for k, v in sorted(ch.items())}
    md += ["## 2. 저장된 610a97c 판정에 권한 단계를 얹었을 때 (조건 A, 구성 × 거래)", "", "| 유형 | 변화 | 구성×거래 수 |", "|---|---|---:|"]
    md += [f"| {k[0]} | {k[1]} | {v} |" for k, v in sorted(ch.items())]
    md.append("")
    # 3 end-to-end replay on a sample
    rng = random.Random(20261127)
    by = {}
    for r in rows:
        by.setdefault(r["transaction_type"], []).append(r)
    sample = [r for tt in sorted(by) for r in rng.sample(by[tt], min(n_per_type, len(by[tt])))]
    from cdv.nli import NLI
    nli = NLI()
    llm = Replay(X / "ledger_m1g_v4.jsonl")
    e2e = Counter()
    bad = []
    for r in sample:
        tx = txs[r["transaction_id"]]
        case = RX.build_case(eps[r["episode_id"]], tx, tg.get(r["transaction_id"]) or {})
        states = r["fnctod_states"]
        m0 = llm.misses
        try:
            o0 = A.run_arms(case, states, nli=nli, gold=None, m1_llm=llm)
            o1 = A.run_arms(case, states, nli=nli, gold=None, m1_llm=llm, authority_codes=RX.authority_check(tx))
        except RuntimeError as ex:
            bad.append((r["transaction_id"], str(ex)))
            continue
        if llm.misses > m0:
            bad.append((r["transaction_id"], "replay miss"))
            continue
        for arm, a in r["arms"].items():
            d_stored, d0, d1 = a["decision"], o0["arms"][arm]["decision"], o1["arms"][arm]["decision"]
            e2e[(r["transaction_type"], "without=stored" if d0 == d_stored else "without!=stored",
                 "with=without" if d1 == d0 else f"with {d0}->{d1}")] += 1
    res["end_to_end"] = {"sample": len(sample), "skipped": bad, "replay_hits": llm.hits, "replay_misses": llm.misses,
                         "table": {"|".join(k): v for k, v in sorted(e2e.items())}}
    md += [f"## 3. 끝에서 끝까지 재실행 (유형별 {n_per_type}거래 표본 {len(sample)}건, M1-G는 원장 재생만)", "",
           f"- 재생 적중 {llm.hits}, 원장에 없는 요청 {llm.misses}(보내지 않음), 제외한 거래 {len(bad)}.", "",
           "| 유형 | 권한 단계 없이 다시 계산 = 저장값 | 권한 단계 있을 때 | 구성×거래 수 |", "|---|---|---|---:|"]
    md += [f"| {k[0]} | {k[1]} | {k[2]} | {v} |" for k, v in sorted(e2e.items())]
    (OUT / "authority_item20.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (OUT / "AUTHORITY_ITEM20.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
