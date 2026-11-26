"""Post-hoc measurement correction of PLAN_v3 (no model calls, rules unchanged, PLAN_v3 files untouched).

Leak (NOTES_POSTHOC.md 1): the PLAN_v3 harness verified with every shopper turn, including turns after the
payment-consent request. Here the decision point t is fixed per journey and only what precedes t is used:
  t = last payment-consent request (wallet/system confirm message in checkout/payment stage, or a
      create_checkout_mandate call)                         -> the final cart is the one put up for consent
  t = first `done` tool call if the journey has no consent step (cart handed over)
  t = end of dialogue otherwise
FnCTOD arms are replayed from the stored per-turn states (state at the last shopper turn before t), with the
same rules, NLI model, known-brand list (built from truncated states) and decision precedence as run.py.
The plain-LLM arm read the whole dialogue in one call and cannot be truncated offline; it is not corrected here.

Decisions are reported as ALLOW / CLARIFY / DENY separately, original (leaky) next to corrected.
Self-check: every journey is first replayed WITHOUT truncation; that must give the stored PLAN_v3 decision
for all three FnCTOD arms exactly, or the script stops.
Output: results/e_m1_20261126/corrected_truncation/{summary.json, TABLES.md}
Usage:  .venv/Scripts/python.exe eval/e_m1/recompute_truncated.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "m1_v2"))
import diagnose as D  # noqa: E402
from cdv import verdict  # noqa: E402
from cdv.m1 import Ledger, UserTurn  # noqa: E402
from cdv.pipeline import cart_check, run_verified, state_to_entries  # noqa: E402

RES = ROOT / "results" / "e_m1_20261126"
OUT = RES / "corrected_truncation"
SETS = {"R1": "R1_test_cross_store", "R3": "R3_test_cross_store", "R2": "R2_test_cross_store"}
LEGIT, VIOL = {"RIGHT", "RIGHT_BY_LUCK"}, {"WRONG", "WRONG_HIDDEN"}
ARMS = ("fnctod", "fnctod_r", "fnctod_rn")
PC = "set_purchase_conditions"


def decision_point(T):
    pts = D.consent_points(T)
    if pts:
        return max(pts), "consent_request"
    done = [x["seq"] for x in T if x["kind"] == "tool_call" and x["tool"] == "done"]
    if done:
        return min(done), "cart_handover"
    return (max(x["seq"] for x in T) + 1 if T else 0), "end_of_dialogue"


def cart_of(eid):
    c = D.jl(D.load_cart(eid)) or {}
    return [{"title": l.get("title") or "", "unit_price": (l.get("unit_price") or 0) / 100, "quantity": l.get("quantity") or 1}
            for l in c.get("lines") or []]


def replay(r, T, nli, no_cut=False):
    """no_cut=True replays the whole dialogue; it must give the stored PLAN_v3 decisions exactly (self-check)."""
    cut, kind = (float("inf"), "none(self-check)") if no_cut else decision_point(T)
    # same user-turn definition as run.py::load_dialogues (message, non-blank text, shopper)
    ut = [UserTurn(f"s{x['seq']}", x["seq"], x["text"]) for x in T
          if x["kind"] == "message" and x["actor"] == "shopper" and (x["text"] or "").strip() and x["seq"] < cut]
    states = [dict(s, seq=int(s["turn_id"][1:])) for s in r.get("fnctod_states") or []]
    trunc = [s for s in states if s["seq"] < cut]
    cart = cart_of(r["episode_id"])
    out = {"cut_kind": kind, "n_user_turns_dropped": sum(1 for x in T if x["kind"] == "message" and x["actor"] == "shopper"
                                                         and x["seq"] >= cut), "arms": {}}
    final = trunc[-1]["state"] if trunc else {}
    led = Ledger(1, tuple(state_to_entries(final).values()))
    out["arms"]["fnctod"] = verdict.plan_v3(None, cart_check(led, cart)[0])
    brands = sorted({str(b) for st in trunc for k in ("brand_include", "brand_exclude")
                     for b in ((st["state"].get(PC) or {}).get(k) or [])})
    for name, use in (("fnctod_r", None), ("fnctod_rn", nli)):
        res = run_verified(trunc, ut, nli=use, known_brands=brands)
        d, _ = cart_check(res["ledger"], cart)
        out["arms"][name] = verdict.plan_v3(res["hint"], d)          # common decision function
    return out


def wilson(k, n, z=1.96):
    if not n:
        return (None, None)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, round(100 * (c - h), 1)), min(100.0, round(100 * (c + h), 1)))


def tab(decs):
    n = len(decs)
    c = Counter(decs)
    return {"n": n, **{k: c.get(k, 0) for k in ("ALLOW", "CLARIFY", "DENY")},
            "blocked_pct": round(100 * (n - c.get("ALLOW", 0)) / n, 1) if n else None,
            "blocked_ci95": wilson(n - c.get("ALLOW", 0), n)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = {k: [json.loads(l) for l in (RES / f"rows_{v}.jsonl").read_text(encoding="utf-8").splitlines() if l]
            for k, v in SETS.items()}
    eids = {r["episode_id"] for rs in rows.values() for r in rs}
    allsp = ("train", "validation", "test_cross_store", "test_cross_template")   # R2 was drawn from all splits
    T = D.load_turns(eids, splits=allsp)
    for m in D.load_msgs(eids, splits=allsp):
        D._CART[m["episode_id"]] = m["final_cart"]
    from cdv.nli import NLI
    nli = NLI()
    summ = {"note": __doc__.split("\n\n")[0], "sets": {}}
    per_row = []
    for s, rs in rows.items():
        acc = {a: {"orig": {"legit": [], "viol": []}, "corr": {"legit": [], "viol": []}} for a in ARMS}
        plain = {"legit": [], "viol": []}
        kinds, changed, dropped = Counter(), Counter(), 0
        for r in rs:
            grp = "legit" if r["outcome"] in LEGIT else "viol"
            assert T.get(r["episode_id"]), f"no turns for {r['episode_id']}"
            assert cart_of(r["episode_id"]), f"no cart for {r['episode_id']}"
            full = replay(r, T[r["episode_id"]], nli, no_cut=True)
            bad = {a: (full["arms"][a], r["arms"][a]["decision"]) for a in ARMS if full["arms"][a] != r["arms"][a]["decision"]}
            assert not bad, f"self-check failed (no cut != PLAN_v3) {r['episode_id']}: {bad}"
            rp = replay(r, T[r["episode_id"]], nli)
            kinds[rp["cut_kind"]] += 1
            dropped += rp["n_user_turns_dropped"] > 0
            plain[grp].append(r["arms"]["plain"]["decision"])
            for a in ARMS:
                o = r["arms"][a]["decision"]
                acc[a]["orig"][grp].append(o)
                acc[a]["corr"][grp].append(rp["arms"][a])
                changed[a] += o != rp["arms"][a]
            per_row.append({"set": s, "episode_id": r["episode_id"], "outcome": r["outcome"], **rp,
                            "orig": {a: r["arms"][a]["decision"] for a in ARMS}})
        S = {"n": len(rs), "decision_point": dict(kinds), "journeys_with_user_turns_dropped": dropped,
             "decisions_changed": dict(changed),
             "plain_uncorrected": {g: tab(v) for g, v in plain.items()}, "arms": {}}
        for a in ARMS:
            S["arms"][a] = {}
            for ver in ("orig", "corr"):
                L, V = tab(acc[a][ver]["legit"]), tab(acc[a][ver]["viol"])
                sel = round(V["blocked_pct"] - L["blocked_pct"], 1) if L["n"] and V["n"] else None
                S["arms"][a][ver] = {"legit": L, "viol": V, "selectivity_pp": sel}
        summ["sets"][s] = S
    (OUT / "summary.json").write_text(json.dumps(summ, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (OUT / "rows.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in per_row),
                                    encoding="utf-8", newline="\n")
    md = ["# PLAN_v3 판정 시점 교정 (사후, 무과금, 규칙 변경 없음)", "",
          "- 원 결과(누설 포함)와 교정 결과(결제 요청 직전까지)를 나란히 둔다. 원 결과 파일은 고치지 않았다.",
          "- 판정 시점: 마지막 결제 동의 요청 직전 / 결제 단계가 없으면 첫 `done`(장바구니 전달) 직전.",
          "- FnCTOD 세 팔만 교정했다(저장된 턴별 상태 재사용). 일반 LLM 팔은 대화 전체를 한 번에 읽어 오프라인 교정이 불가능하다(원 결과만 표시).",
          "- test_cross_store는 이미 본 데이터다. 이 표는 측정 교정이지 설계 확정용이 아니다.", ""]
    for s, S in summ["sets"].items():
        md += [f"## {s} (n={S['n']}; 판정 시점 {S['decision_point']}; 판정에서 빠진 쇼핑객 발화가 있는 여정 {S['journeys_with_user_turns_dropped']})", "",
               "| 팔 | 버전 | 정상 n | 정상 CLARIFY | 정상 DENY | 정상 차단% [95% CI] | 위반 n | 위반 CLARIFY | 위반 DENY | 위반 차단% [95% CI] | 선별성(pp) |",
               "|---|---|---:|---:|---:|---|---:|---:|---:|---|---:|"]
        P = S["plain_uncorrected"]
        md.append(f"| plain | 원(누설) | {P['legit']['n']} | {P['legit']['CLARIFY']} | {P['legit']['DENY']} | {P['legit']['blocked_pct']} {P['legit']['blocked_ci95']} | "
                  f"{P['viol']['n']} | {P['viol']['CLARIFY']} | {P['viol']['DENY']} | {P['viol']['blocked_pct']} {P['viol']['blocked_ci95']} | "
                  f"{round(P['viol']['blocked_pct'] - P['legit']['blocked_pct'], 1) if P['legit']['n'] and P['viol']['n'] else '–'} |")
        for a in ARMS:
            for ver, lab in (("orig", "원(누설)"), ("corr", "교정")):
                x = S["arms"][a][ver]
                L, V = x["legit"], x["viol"]
                md.append(f"| {a} | {lab} | {L['n']} | {L['CLARIFY']} | {L['DENY']} | {L['blocked_pct']} {L['blocked_ci95']} | "
                          f"{V['n']} | {V['CLARIFY']} | {V['DENY']} | {V['blocked_pct']} {V['blocked_ci95']} | {x['selectivity_pp']} |")
        md += ["", f"판정이 바뀐 여정 수: {S['decisions_changed']}", ""]
    (OUT / "TABLES.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
