"""AV2+ — field-matched A-VIP comparison arm (researcher decision 2026-11-27; AUXILIARY, not in the Holm family).

Definition (fixed in results/frozen_610a97c/AV2PLUS_DEFINITION.md before v4b eval is opened):
  AV2+ = AV2 (A-VIP STRICT + binding + capture on an empty-scope mandate, then the PLAN_v3 cart check on the
         ACCUMULATED extracted conditions, eval/integrated/arms.py::avip_simple(env, dst_acc(states)))
         + the three payment-consent checks of the M2 gate, applied with the frozen function
           cdv/v2/scope.py::checkout_violations to a scope built (frozen ledger_to_mandate) from the SAME accumulated
           conditions: payment total incl. fees vs budget, fulfillment method, deadline days.
         Applied exactly where full_gate applies them (arms.py:120-123): only if the decision so far is not DENY;
         any violation -> DENY. A fact the payment request does not carry leaves that check unverified (counted,
         never turned into CLARIFY: the unverified-at-consent policy #18 is NOT part of AV2+).
  Nothing else of M2 is added (no UNKNOWN_ATTR, no structured-brand rule, no bundle must-include, no clauses, no E2,
  no selection, no versions). No system code is changed; frozen functions are imported.
Free: uses the stored extraction states (P4 / R-v4g extraction is the same cached extraction) and gold states for the
stale-version part. No model calls.

Parts (v4 dev unless noted):
  1 transactions, conditions A and B: AV2+ next to AV0, AV1, AV2, B2, B3, B4, PRECHECK; per violated field
  2 AV2 -> B2 and AV2+ -> B2 discordant transactions on context_only, by blocking component; every transaction not
    explained by the three consent-time checks listed one by one
  3 matched stockout pairs (96), conditions A and B
  4 prior-version reuse (the 72 episodes of eval/v4check/stale_version.py): AV2+ with the OLD conditions (initial_state)
    and with the NEW conditions (effective_state), next to CDV (v1 under version revocation) and the full gate
  5 validation (CartTrace, P2 extraction, journeys de-duplicated): AV2+ vs AV2 vs B2 vs B3 on the 29 payment-checkable
    violations and the 230 legit journeys, with the same decomposition
Output: results/review_20261127/av2plus/{AV2PLUS.md, av2plus.json, av2plus_rows_*.jsonl}
Usage: .venv/Scripts/python.exe eval/review/av2plus.py [rows tag, default m1g]
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check", "eval/extdata", "eval/m1_v2"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import arms as A  # noqa: E402
import run_ext as RX  # noqa: E402
from cdv.gate import Request, authorize, combined_hash, context_record  # noqa: E402
from cdv.mandate import VersionRegistry  # noqa: E402
from paired_compare import component  # noqa: E402

X = ROOT / "results" / "extdata_20261126"
DEV = ROOT / "results" / "integrated_dev_20261126"
OUT = ROOT / "results" / "review_20261127" / "av2plus"
V4 = Path(r"C:/ct/external/carttrace_cdv_evaluation_v4/dev")
NAME, SPLIT, M1G_LEDGER = "v4", "dev", "v4"
CONSENT3 = {"총액(수수료 포함)", "수령 방식(동의 시점)", "기한(동의 시점)"}
ARMS = ("AV0", "AV1", "AV2", "AV2+", "B2", "B3", "B4", "PRECHECK")


def jl(p):
    p = Path(p)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def av2plus_entries(env, case, entries: dict):
    """AV2's checks on `entries`, then the three consent-time checks of full_gate on a scope from the same entries."""
    d, codes = A.avip_simple(env, None)                                   # A-VIP part (empty-scope mandate)
    if d != "ALLOW":
        return d, list(codes), [], d
    d, codes = A.cart_check(A.Ledger(1, tuple(entries.values())), A._cart_lines(case))   # AV2's PLAN_v3 cart check
    codes, d_av2, unk = list(codes), d, []
    if d != "DENY":
        e = dict(entries)
        e.pop("ptype", None)                                              # as raw_ctx: product type is not a scope field
        scope = A.ledger_to_mandate(A.Ctx(e, None, None), case.reg, case.seller, f"m-{case.episode_id}", 1, env.session).primary
        cv, unk = A.checkout_violations(scope, case.checkout_facts)
        if cv:
            d, codes = "DENY", codes + ["OUT_OF_SCOPE"] + cv
    return d, codes, unk, d_av2


def states_before(r, t):
    return sorted([{"seq": int(s["turn_id"][1:]), "state": s["state"]} for s in r["fnctod_states"] if int(s["turn_id"][1:]) < t],
                  key=lambda s: s["seq"])


def comps(codes, m1_asks=False):
    c = component(codes, m1_asks)
    return [x.strip() for x in c.split(",")] if c != "-" else []


def acd(G, arm):
    c = Counter(r["arms"][arm]["decision"] for r in G if arm in r["arms"])
    return f"{c['ALLOW']}/{c['CLARIFY']}/{c['DENY']}"


def main(tag="m1g"):
    OUT.mkdir(parents=True, exist_ok=True)
    sfx = f"_{tag}" if tag else ""
    eps = {e["episode_id"]: e for e in jl(V4 / "episodes.jsonl")}
    txs = {t["transaction_id"]: t for t in jl(V4 / "transactions.jsonl")}
    tg = {g["transaction_id"]: g for g in jl(V4 / "transaction_gold.jsonl")}
    eg = {g["episode_id"]: g for g in jl(V4 / "episode_gold.jsonl")}
    mx = {m["challenge_id"]: m for m in jl(V4 / "matched_stockout.jsonl")}
    pre = {"A": {x["id"]: x["precheck"] for x in jl(X / f"baselines_{NAME}_{SPLIT}.jsonl")},
           "B": {x["id"]: x["precheck"] for x in jl(X / f"baselines_{NAME}_{SPLIT}_B.jsonl")}}
    res = {"rows_tag": tag}
    md = [f"# AV2+ (필드를 맞춘 A-VIP 비교군) — 보조 비교, Holm 대상 아님 (행 `rows_v4_dev_*{sfx}`, 모델 호출 0)", "",
          "- 정의: `results/frozen_610a97c/AV2PLUS_DEFINITION.md`. AV2 + 결제 동의 시점 3검사(수수료 포함 총액, 수령 방식, 기한), AV2가 누적한 추출 조건 그대로.",
          "- 수치 표기: AV0–AV2, B2–B4는 " + ("[고정 후 dev] (R-v4g, 주 M1 = M1-G)" if tag else "[고정 전 dev] (배선 시험)")
          + ", PRECHECK는 [고정 후 dev] 별도 실행, AV2+는 같은 추출 상태로 무료 계산.", ""]
    # ---------- parts 1-3 on v4 dev
    allrows = {}
    for c in ("A", "B"):
        R = jl(X / f"rows_{NAME}_{SPLIT}_{c}{sfx}.jsonl")
        M = jl(X / f"rows_{NAME}_{SPLIT}_{c}{sfx}_matched.jsonl")
        if not R:
            continue
        st_by_ep = {}
        out = []
        for r in R:
            tx = txs[r["transaction_id"]]
            case = RX.build_case(eps[r["episode_id"]], tx, tg.get(r["transaction_id"]) or {})
            env = A.Env(case)
            st = states_before(r, case.t)
            st_by_ep[r["episode_id"]] = r
            d, codes, unk, d_av2 = av2plus_entries(env, case, A.state_to_entries(A.dst_acc(st)))
            assert d_av2 == r["arms"]["AV2"]["decision"] or r["arms"]["AV2"]["decision"] != "ALLOW" and d_av2 != "ALLOW", \
                f"AV2 part differs from the stored AV2 for {r['transaction_id']}"
            r["arms"]["AV2+"] = {"decision": d, "codes": codes, "unverified": unk}
            if r["transaction_id"] in pre[c]:
                r["arms"]["PRECHECK"] = {"decision": pre[c][r["transaction_id"]], "codes": None}
            out.append({"transaction_id": r["transaction_id"], "AV2+": d, "codes": codes, "unverified": unk})
        (OUT / f"av2plus_rows_v4dev_{c}{sfx}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out),
                                                                encoding="utf-8", newline="\n")
        for m in M:
            src = st_by_ep.get(m["episode_id"])
            if src is None:
                continue
            case = RX.build_case(eps[m["episode_id"]], mx[m["challenge_id"]], {})
            env = A.Env(case)
            d, codes, unk, _ = av2plus_entries(env, case, A.state_to_entries(A.dst_acc(states_before(src, case.t))))
            m["arms"]["AV2+"] = {"decision": d, "codes": codes}
            if m["challenge_id"] in pre[c]:
                m["arms"]["PRECHECK"] = {"decision": pre[c][m["challenge_id"]]}
        allrows[c] = (R, M)
        # part 1: by transaction type and by violated field
        md += [f"## 1. 조건 ({c}): 유형별 ALLOW/CLARIFY/DENY (합계는 유형 비율에 좌우되므로 보조)", "",
               "| 유형 (n) | " + " | ".join(ARMS) + " |", "|---|" + "---|" * len(ARMS)]
        for tt in ("normal", "context_only", "both", "authority_only"):
            G = [r for r in R if r["transaction_type"] == tt]
            md.append(f"| {tt} ({len(G)}) | " + " | ".join(acd(G, a) for a in ARMS) + " |")
        md += ["", f"### 위반 필드별 (조건 {c}, context_only, 정답 context_reasons; '단독'은 그 필드만 위반한 거래)", "",
               "| 필드 | n | " + " | ".join(f"{a} ALLOW" for a in ARMS) + " |", "|---|---:|" + "---:|" * len(ARMS)]
        ctx = [r for r in R if r["transaction_type"] == "context_only"]
        fields = Counter(f for r in ctx for f in (tg[r["transaction_id"]].get("context_reasons") or []))
        res[f"by_field_{c}"] = {}
        for f, _ in fields.most_common():
            for lab, G in ((f, [r for r in ctx if f in (tg[r["transaction_id"]].get("context_reasons") or [])]),
                           (f + " 단독", [r for r in ctx if (tg[r["transaction_id"]].get("context_reasons") or []) == [f]])):
                if not G:
                    continue
                cells = [sum(r["arms"][a]["decision"] == "ALLOW" for r in G if a in r["arms"]) for a in ARMS]
                res[f"by_field_{c}"][lab] = dict(zip(ARMS, cells), n=len(G))
                md.append(f"| {lab} | {len(G)} | " + " | ".join(map(str, cells)) + " |")
        md.append("")
        # part 2: discordance with B2 (condition A only)
        if c == "A":
            md += ["## 2. B2와의 차이 (조건 A, context_only)", ""]
            for base in ("AV2", "AV2+"):
                only_b2 = [r for r in ctx if r["arms"][base]["decision"] == "ALLOW" and r["arms"]["B2"]["decision"] != "ALLOW"]
                only_base = [r for r in ctx if r["arms"]["B2"]["decision"] == "ALLOW" and r["arms"][base]["decision"] != "ALLOW"]
                cc = Counter(x for r in only_b2 for x in comps(r["arms"]["B2"]["codes"]))
                unexpl = [r for r in only_b2 if not (set(comps(r["arms"]["B2"]["codes"])) & CONSENT3)]
                res[f"{base}_vs_B2"] = {"base_allows_B2_blocks": len(only_b2), "B2_allows_base_blocks": len(only_base),
                                        "B2_components": dict(cc), "not_explained_by_consent3": len(unexpl)}
                md += [f"### {base} 대 B2", "",
                       f"- {base}는 허용, B2는 막음: **{len(only_b2)}**건. B2는 허용, {base}는 막음: {len(only_base)}건.",
                       "- B2가 막은 구성 요소(중복 가능): " + (", ".join(f"{k} {v}" for k, v in cc.most_common()) or "없음"),
                       f"- 세 검사(수수료 포함 총액·수령 방식·기한)로 설명되지 않는 거래: {len(unexpl)}건", ""]
                if unexpl:
                    md += ["| 거래 | 정답 위반 필드 | B2 판정 | B2 사유 코드 | " + base + " 사유 코드 |", "|---|---|---|---|---|"]
                    for r in unexpl:
                        md.append(f"| `{r['transaction_id'][-8:]}` | {', '.join(tg[r['transaction_id']].get('context_reasons') or [])} | "
                                  f"{r['arms']['B2']['decision']} | {', '.join(map(str, r['arms']['B2']['codes']))} | "
                                  f"{', '.join(map(str, r['arms'][base].get('codes') or [])) or '-'} |")
                    md.append("")
                if only_base:
                    md += [f"- B2는 허용하고 {base}만 막은 거래의 {base} 사유: "
                           + ", ".join(f"{k} {v}" for k, v in Counter(x for r in only_base for x in comps(r["arms"][base].get("codes"))).most_common()), ""]
        # part 3: matched
        if M:
            md += [f"## 3. 대응 쌍 96건 — 조건 ({c})", "", "| 사례 | 참조 판정 | n | " + " | ".join(ARMS) + " |", "|---|---|---:|" + "---|" * len(ARMS)]
            by = defaultdict(list)
            for m in M:
                by[(m.get("intent_case"), m.get("reference_verdict"))].append(m)
            for k in sorted(by, key=str):
                G = by[k]
                md.append(f"| {k[0]} | {k[1]} | {len(G)} | " + " | ".join(acd(G, a) for a in ARMS) + " |")
            md.append("")
    # ---------- part 4: prior-version reuse (v4 dev only: the stale-version design lives there)
    if (NAME, SPLIT) != ("v4", "dev"):
        (OUT / f"av2plus{sfx}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        (OUT / f"AV2PLUS{sfx}.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
        print("\n".join(md))
        return
    keep = set(eps) - set(json.loads((X / f"exclusion_{NAME}_{SPLIT}.json").read_text(encoding="utf-8"))["excluded_episodes"])
    eps72 = sorted({t["episode_id"] for t in txs.values() if t["episode_id"] in keep and eg[t["episode_id"]].get("accepted_changes")
                    and (tg.get(t["transaction_id"]) or {}).get("transaction_type") == "normal"})
    tab = defaultdict(Counter)
    for e in eps72:
        ep, g = eps[e], eg[e]
        cat = {x["sku"]: x for x in ep["catalog"]}
        for t in [t for t in txs.values() if t["episode_id"] == e]:
            gt = tg.get(t["transaction_id"]) or {}
            if gt.get("transaction_type") not in ("normal", "context_only"):
                continue
            case = RX.build_case(ep, t, gt)
            env = A.Env(case)
            mid = f"m-{case.episode_id}"
            old, new = (RX.gold_ctx({"effective_state": g[k]}, cat) for k in ("initial_state", "effective_state"))
            m1 = A.ledger_to_mandate(old, case.reg, case.seller, mid, 1, env.session).signed(A.USER_SK)
            vr = VersionRegistry()
            vr.publish(mid, 1)
            vr.publish(mid, 2)
            c_r = context_record(m1, None, [])
            d_cdv = authorize(Request(m1, A.USER_PK, vr, env.session, case.offers, case.catalog, case.cart, env.avip_r, c_r,
                                      combined_hash(A.avip.record_hash(env.avip_r), c_r), env.evid, A.ISSUERS, A.NonceStore(), A.NOW)).decision
            d_new_full = env.full_gate(A.ledger_to_mandate(new, case.reg, case.seller, mid, 2, env.session))[0]
            d_old_full = env.full_gate(A.ledger_to_mandate(old, case.reg, case.seller, mid, 1, env.session))[0]
            d_old_p = av2plus_entries(env, case, dict(old.entries))[0]
            d_new_p = av2plus_entries(env, case, dict(new.entries))[0]
            tab[gt["transaction_type"]][(d_new_full, d_cdv, d_old_full, d_new_p, d_old_p)] += 1
    res["stale"] = {"episodes": len(eps72), "by_type": {k: {"|".join(kk): v for kk, v in c_.items()} for k, c_ in tab.items()}}
    md += ["## 4. 이전 권한 재사용 (안정 버전 시험의 72여정, 정답 조건 사용)", "",
           f"- 여정 {len(eps72)}. 각 거래에서: 새 조건의 전체 게이트 / CDV(구버전 v1, 버전 폐기 검사) / 폐기 검사 없는 구버전 전체 게이트 / "
           "AV2+(새 조건) / AV2+(구 조건). AV2+에는 버전 개념이 없어 구 조건이 남아 있으면 그 조건으로 판정한다.", "",
           "| 유형 | 새 조건 전체 게이트 | CDV v1 | v1 폐기 없음 | AV2+ 새 조건 | AV2+ 구 조건 | 건수 |", "|---|---|---|---|---|---|---:|"]
    for tt, c_ in tab.items():
        for k, v in sorted(c_.items(), key=lambda kv: -kv[1]):
            md.append(f"| {tt} | " + " | ".join(k) + f" | {v} |")
    for tt, c_ in tab.items():
        n = sum(c_.values())
        old_allow = sum(v for k, v in c_.items() if k[4] == "ALLOW")
        cdv_allow = sum(v for k, v in c_.items() if k[1] == "ALLOW")
        md.append(f"- {tt} {n}건: AV2+(구 조건) ALLOW {old_allow}, CDV v1 ALLOW {cdv_allow}.")
    md.append("")
    # ---------- part 5: validation (CartTrace)
    import env as E
    vrows = {}
    for s in ("V1", "V3", "V2"):
        for x in jl(DEV / f"extract_{s}.jsonl"):
            vrows.setdefault(x["episode_id"], x)
    drows = {}
    for x in jl(DEV / "dev_rows_frozen_m1g.jsonl"):
        drows.setdefault(x["episode_id"], x)
    cases = E.build_cases(set(vrows))
    vres = []
    for e, x in vrows.items():
        c_ = cases[e]
        env = A.Env(c_)
        st = sorted([{"seq": int(s["turn_id"][1:]), "state": s["state"]} for s in x["fnctod_states"] if int(s["turn_id"][1:]) < c_.t],
                    key=lambda s: s["seq"])
        d, codes, unk, d_av2 = av2plus_entries(env, c_, A.state_to_entries(A.dst_acc(st)))
        r = drows[e]
        r["arms"]["AV2+"] = {"decision": d, "codes": codes, "unverified": unk}
        vres.append(r)
    V = [r for r in vres if r["pay_viol"]]
    L = [r for r in vres if r["outcome"] in ("RIGHT", "RIGHT_BY_LUCK")]
    blk = lambda r, a: r["arms"][a]["decision"] != "ALLOW"  # noqa: E731
    md += ["## 5. validation (CartTrace, 고정 후 dev 재실행, 여정 단위 중복 제거)", "",
           f"| 비교군 | 결제 조건 위반 {len(V)} 차단 | 정상 {len(L)} 차단 | 위반 A/C/D | 정상 A/C/D |", "|---|---:|---:|---|---|"]
    res["validation"] = {}
    for a in ("AV0", "AV1", "AV2", "AV2+", "B2", "B3", "B4"):
        bv, bl = sum(blk(r, a) for r in V), sum(blk(r, a) for r in L)
        res["validation"][a] = {"viol_blocked": bv, "legit_blocked": bl}
        md.append(f"| {a} | {bv} | {bl} | {acd(V, a)} | {acd(L, a)} |")
    for base in ("AV2", "AV2+"):
        ob = [r for r in V if blk(r, "B2") and not blk(r, base)]
        oa = [r for r in V if blk(r, base) and not blk(r, "B2")]
        md += ["", f"- 위반 {len(V)}건, {base} 대 B2: B2만 막음 {len(ob)} ("
               + (", ".join(f"{k} {v}" for k, v in Counter(x for r in ob for x in comps(r['arms']['B2']['codes'])).most_common()) or "-")
               + f"), {base}만 막음 {len(oa)} ("
               + (", ".join(f"{k} {v}" for k, v in Counter(x for r in oa for x in comps(r['arms'][base].get('codes'))).most_common()) or "-") + ")"]
        lb = [r for r in L if blk(r, "B2") and not blk(r, base)]
        la = [r for r in L if blk(r, base) and not blk(r, "B2")]
        md += [f"- 정상 {len(L)}건, {base} 대 B2: B2만 막음 {len(lb)} ("
               + (", ".join(f"{k} {v}" for k, v in Counter(x for r in lb for x in comps(r['arms']['B2']['codes'])).most_common()) or "-")
               + f"), {base}만 막음 {len(la)}"]
    md.append(f"- AV2+에서 결제 요청에 사실이 없어 확인하지 못한 검사(미검증, CLARIFY로 바꾸지 않음): "
              + ", ".join(f"{k} {v}" for k, v in Counter(u for r in vres for u in r["arms"]["AV2+"]["unverified"]).most_common()))
    (OUT / f"av2plus{sfx}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (OUT / f"AV2PLUS{sfx}.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))




def _cli():
    """--data <dataset root> --name <label> --split <split> --m1g-ledger <label>: defaults = v4 dev (as before)."""
    import argparse
    global V4, NAME, SPLIT, M1G_LEDGER, OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("tag", nargs="?", default="m1g")
    ap.add_argument("--data", default=None)
    ap.add_argument("--name", default="v4")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--m1g-ledger", default=None, help="label of ledger_m1g_<label>.jsonl (default: --name)")
    a = ap.parse_args()
    NAME, SPLIT = a.name, a.split
    M1G_LEDGER = a.m1g_ledger or a.name
    if a.data:
        V4 = Path(a.data) / a.split
    if (NAME, SPLIT) != ("v4", "dev"):
        OUT = OUT.parent / f"{OUT.name}_{NAME}_{SPLIT}"
    return a.tag

if __name__ == "__main__":
    main(_cli())
