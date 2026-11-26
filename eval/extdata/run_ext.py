"""Integrated runner for the external synthetic datasets (v2 common format; v3g / v3c extras optional).

Required input (v2 common fields):
  <split>/episodes.jsonl      episode_id, dialogue[{turn_id, role: user|assistant|tool, text}], catalog[{sku, product,
                              title, product_type, brand, attributes, unit_minor, stock, ...}], store_id, currency
  <split>/transactions.jsonl  transaction_id, episode_id, checkout{lines[{sku, brand, unit_minor, attributes, quantity}],
                              fulfillment, days, fees_minor}, payment_request{...}, payment_grant{...}
Scoring only (never an arm input): transaction_gold.jsonl (expected_checkout, transaction_type, context_violation,
  authority_violation), episode_gold.jsonl (source.episode_id for exclusion; effective_state for the U reference).
Optional extras: catalog[].seller_description (v3g; A-VIP label / seller prose), candidate_operations (v3g, v3c;
  ignored here: this is the natural-extraction path), matched_stockout*.jsonl (separate view), integrity_* (separate).
Pipeline per transaction: dialogue (user/assistant turns to the extractor; tool turns are environment text: they go
  to M1 as non-user text and to A-VIP as seller prose, never to the extractor) -> FnCTOD (one extraction per episode,
  shared by all arms) -> eval/integrated/arms.py B0-B4 (+ U reference from episode_gold.effective_state).
  checkout.fulfillment / checkout.days are the consent-point facts (CONSENT_CHECKOUT_CHECK).
Authority axis (payment_request vs payment_grant) is computed separately and NOT merged into the main decision.
Exclusion: episodes whose source journey was already seen (exposure registry, E-M1 rows, P2 dev, G1/G1v2 bases) or is in
  the sealed sample are dropped; the dropped IDs and the final n are written before any model call (--dry-run).
Usage:
  dry:  .venv/Scripts/python.exe eval/extdata/run_ext.py --data <dir> --name v3g --split dev --dry-run
  live: ... --budget 0.60   (after plan approval)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("", "eval/integrated", "eval/e_m1", "eval/seal", "eval/v3check"):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
import arms as A  # noqa: E402
import run as R  # noqa: E402  (DryLLM)
from cdv.extract import FnCTOD, OpenAIResponses, PlainLLM, Turn  # noqa: E402
from cdv.m1 import UserTurn  # noqa: E402
from cdv.v2.candidates import Product, Registry  # noqa: E402
from cdv.v2.m1v2 import Ctx  # noqa: E402
from cdv.v2.scope import LineV2  # noqa: E402
from draw_sealed import load_sealed, seen_ids  # noqa: E402
from env import IntegratedCase  # noqa: E402
from inject import entries_from  # noqa: E402

OUT = ROOT / "results" / "extdata_20261126"


def jl(p: Path):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def build_case(ep: dict, tx: dict, gold_tx: dict) -> IntegratedCase:
    seller = ep.get("store_id") or "store"
    turns = ep["dialogue"]
    if not any(t["role"] == "user" for t in turns):
        raise SystemExit(f"{ep['episode_id']}: no user turn")
    if not tx["checkout"]["lines"]:
        raise SystemExit(f"{tx['transaction_id']}: empty checkout")
    ut = [UserTurn(f"s{i}", i, t["text"]) for i, t in enumerate(turns) if t["role"] == "user"]
    nonuser = [(i, t["text"]) for i, t in enumerate(turns) if t["role"] in ("assistant", "tool")]
    reg = Registry()
    offers, catalog, unavailable = [], {}, []
    for c in ep["catalog"]:
        sku = str(c["sku"])
        reg.products[sku] = Product(sku, c.get("title") or "", c.get("brand"),
                                    " ".join([c.get("title") or "", c.get("product_type") or ""]),
                                    c.get("seller_description") or "", {sku: {"price": c["unit_minor"] / 100,
                                                                              "available": (c.get("stock") or 0) > 0 if c.get("stock") is not None else None,
                                                                              "title": c.get("title") or ""}}, 0)
        reg.variant_to_product[sku] = sku
        prose = c.get("listing_text") or c.get("seller_description") or ""      # v4: listing_text; v3g: seller_description
        offers.append({"cart_id": sku, "seller": seller, "label": (c.get("title") or "") + (". " + prose if prose else ""),
                       "amount": f"{c['unit_minor'] / 100:.2f}", "currency": c.get("currency") or ep.get("currency") or "USD"})
        catalog[(seller, sku)] = LineV2(seller, sku, c["unit_minor"] / 100, 1, c.get("brand"), sku, frozenset(),
                                        title=c.get("title") or "", kind_text=" ".join([c.get("title") or "", c.get("product_type") or ""]),
                                        product_id=sku, brand_known=bool(c.get("brand")))
        if c.get("stock") == 0:
            unavailable.append((seller, sku))       # structured catalog stock = platform fact
    for t in turns:                                 # v4: platform tool turns carry structured stock for a listing
        if t.get("role") == "tool" and t.get("source") == "platform" and t.get("listing_sku") and t.get("stock") == 0:
            k = (seller, str(t["listing_sku"]))
            if k not in unavailable:
                unavailable.append(k)
    cart = []
    for l in tx["checkout"]["lines"]:
        k = (seller, str(l["sku"]))
        if k in catalog:
            c = catalog[k]
            catalog[k] = LineV2(**{**c.__dict__, "unit_price": l["unit_minor"] / 100, "brand": l.get("brand") or c.brand})
        cart.append((k, int(l.get("quantity") or 1)))
    ful = {"delivery": "ship", "shipping": "ship", "ship": "ship", "pickup": "pickup"}.get(str(tx["checkout"].get("fulfillment") or "").lower())
    return IntegratedCase(ep["episode_id"], "ext", "generated", len(turns), "consent_request", ut, nonuser, reg, seller, offers,
                          catalog, cart, unavailable, checkout_facts={"fulfillment": ful, "max_days": tx["checkout"].get("days"),
                          "payment_total": (sum(l["unit_minor"] * int(l.get("quantity") or 1) for l in tx["checkout"]["lines"])
                                            + int(tx["checkout"].get("fees_minor") or 0)) / 100},
                          scoring={"gold": gold_tx})


def authority_check(tx: dict) -> list:
    """Separate axis: payment request against its grant (never merged into the main decision)."""
    pr, g = tx.get("payment_request") or {}, tx.get("payment_grant") or {}
    bad = []
    for k in ("grant_id", "payer", "payee", "currency"):
        if pr.get(k) != g.get(k):
            bad.append(f"GRANT_{k.upper()}")
    if (pr.get("amount_minor") or 0) > (g.get("max_total_minor") or 0):
        bad.append("GRANT_AMOUNT")
    if pr.get("attempt_at") and g.get("expires_at") and pr["attempt_at"] > g["expires_at"]:
        bad.append("GRANT_EXPIRED")
    return bad


def gold_ctx(eg: dict, catalog_by_sku: dict) -> Ctx:
    """U reference from the gold effective state (scoring side only). Revoked conditions have no key.
    Alternatives {sku: [options]} = unconditional either-or; Substitution {sku: alt} = conditional (platform evidence)."""
    es = {}
    st = eg.get("effective_state") or {}
    for f in ("Price", "Quantity", "Brand", "Bundle", "Fulfillment", "Deadline", "Substitution"):
        if f in st and st[f] not in (None, {}, []):
            for eid, e in entries_from(f, st[f], catalog_by_sku):
                if e is not None:
                    es[eid] = e
    alts = frozenset(str(o) for opts in (st.get("Alternatives") or {}).values() for o in opts) or None
    subs = frozenset(str(v) for v in (st.get("Substitution") or {}).values()) or None
    return Ctx(es, None, frozenset(st.get("Product") or []) or None, alternatives=alts, sub_targets=subs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--name", required=True, help="dataset label, e.g. v3g or v3c")
    ap.add_argument("--split", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default="gpt-6-luna")
    ap.add_argument("--budget", type=float, default=0.60)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--with-matched", action="store_true", help="also score matched_stockout.jsonl (same extraction)")
    ap.add_argument("--m1g", action="store_true", help="main M1 = M1-G (paid basis judgement; separate ledger), adds B3_v2")
    ap.add_argument("--m1g-budget", type=float, default=0.20)
    ap.add_argument("--tag", default="", help="output suffix (rows/summary); never overwrites")
    ap.add_argument("--unverified-policy", default="consent_clarify", choices=["consent_clarify", "record"])
    # runner options added 2026-11-27 (adjustment 21, runner only; defaults = old behaviour)
    ap.add_argument("--m1g-memo", action="store_true",
                    help="within this run, one M1-G call per distinct input shared by all transactions; parallel pre-warm")
    ap.add_argument("--ledger-tag", default="", help="separate extraction and M1-G ledgers (an independent repeat run)")
    ap.add_argument("--m1g-ledger-tag", default=None,
                    help="M1-G ledger tag only (default: --ledger-tag); e.g. run 2 = run-1 extraction + a fresh M1-G ledger")
    ap.add_argument("--seller-to-extractor", action="store_true",
                    help="condition (B): tool turns with source=seller are also given to the extractor (as assistant text)")
    a = ap.parse_args()
    d = a.data / a.split
    eps = {e["episode_id"]: e for e in jl(d / "episodes.jsonl")}
    txs = jl(d / "transactions.jsonl")
    tgold = {g["transaction_id"]: g for g in jl(d / "transaction_gold.jsonl")}
    egold = {g["episode_id"]: g for g in jl(d / "episode_gold.jsonl")}
    if not eps or not txs:
        raise SystemExit("episodes.jsonl and transactions.jsonl are required")
    # ---- exclusion (before any model call)
    seen = seen_ids()
    seen.pop("external_v2_v3g", None)          # the dataset's own sources (used only when sealing)
    seen["sealed_sample"] = load_sealed()
    excl = {}
    for e in eps:
        src = ((egold.get(e) or {}).get("source") or {}).get("episode_id")
        hits = sorted(k for k, s in seen.items() if src in s)
        if hits:
            excl[e] = {"source_episode_id": src, "seen_in": hits}
    keep = [e for e in eps if e not in excl]
    keep_tx = [t for t in txs if t["episode_id"] in set(keep)]
    tag = f"{a.name}_{a.split}" + ("_B" if a.seller_to_extractor else "_A") + (f"_{a.tag}" if a.tag else "") + ("_dry" if a.dry_run else "")
    A.UNVERIFIED_POLICY = a.unverified_policy
    m1_llm = None
    if a.m1g and not a.dry_run:
        mt = a.ledger_tag if a.m1g_ledger_tag is None else a.m1g_ledger_tag
        lt = f"_{mt}" if mt else ""
        m1_llm = OpenAIResponses(a.model, OUT / f"ledger_m1g_{a.name}{lt}.jsonl", a.m1g_budget)
        if a.m1g_memo:
            from m1g_memo import MemoLLM
            m1_llm = MemoLLM(m1_llm)
    OUT.mkdir(parents=True, exist_ok=True)
    files_sha = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(d.glob("*.jsonl"))}
    (OUT / f"exclusion_{a.name}_{a.split}.json").write_text(json.dumps(
        {"dataset": a.name, "split": a.split, "files_sha256": files_sha, "episodes_in": len(eps), "transactions_in": len(txs),
         "excluded_episodes": excl, "episodes_kept": len(keep), "transactions_kept": len(keep_tx)}, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    assert a.dry_run or not (OUT / f"rows_{tag}.jsonl").exists(), f"refusing to overwrite rows_{tag}.jsonl"
    llm = R.DryLLM() if a.dry_run else OpenAIResponses(
        a.model, OUT / f"ledger_{a.name}{('_' + a.ledger_tag) if a.ledger_tag else ''}.jsonl", a.budget)

    def to_extractor(t):
        if t["role"] in ("user", "assistant"):
            return True
        return a.seller_to_extractor and t["role"] == "tool" and t.get("source") == "seller"

    def job(e):
        dlg = [Turn("user" if t["role"] == "user" else "assistant", t["text"], f"s{i}")
               for i, t in enumerate(eps[e]["dialogue"]) if to_extractor(t)]
        try:
            return e, (FnCTOD(llm).run(dlg), PlainLLM(llm).run(dlg))
        except SystemExit:
            raise
        except Exception as ex:  # noqa: BLE001
            return e, ex
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        ext = dict(ex.map(job, keep))
    summ = {"dataset": a.name, "split": a.split, "input_condition": "B (seller turns to extractor)" if a.seller_to_extractor
            else "A (shopper and agent turns only)", "episodes": len(keep), "transactions": len(keep_tx),
            "excluded_episodes": len(excl), "dry_run": a.dry_run}
    if a.dry_run:
        summ["dry_run_estimate"] = {"calls_lower_bound": llm.calls, "input_tokens_est": int(llm.chars_in / 4),
                                    "note": "dry answers select no function: FnCTOD argument calls not counted"}
        (OUT / f"summary_{tag}.json").write_text(json.dumps(summ, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps(summ))
        return
    from cdv.nli import NLI
    nli = NLI()
    if m1_llm is not None and a.m1g_memo:                 # parallel pre-warm of the distinct M1-G requests
        from cdv.v2.m1g_path import run_m1g_path
        from m1g_memo import prewarm

        def pw(item):
            e, txx, gtx = item
            v = ext.get(e)
            if v is None or isinstance(v, Exception):
                return None
            c_ = build_case(eps[e], txx, gtx)
            st = sorted([{"seq": int(s_["turn_id"][1:]), "state": s_["state"]} for s_ in v[0] if int(s_["turn_id"][1:]) < c_.t],
                        key=lambda s_: s_["seq"])
            br = sorted({str(b) for s_ in st for k in ("brand_include", "brand_exclude") for b in ((s_["state"].get(A.PC) or {}).get(k) or [])})
            return run_m1g_path(st, c_.user_turns, c_.agent_turns, c_.reg, c_.t, m1_llm, known_brands=br)
        items = [(t["episode_id"], t, tgold.get(t["transaction_id"]) or {}) for t in keep_tx]
        if a.with_matched:
            items += [(m["episode_id"], m, {}) for m in jl(d / "matched_stockout.jsonl") if m["episode_id"] in set(keep)]
        prewarm_errors = prewarm([lambda it=it: pw(it) for it in items], m1_llm, a.workers)
    rows, failed = [], [{"episode_id": e, "error": repr(v)} for e, v in ext.items() if isinstance(v, Exception)]
    for tx in keep_tx:
        v = ext.get(tx["episode_id"])
        if v is None or isinstance(v, Exception):
            continue
        fn, pl = v
        ep = eps[tx["episode_id"]]
        case = build_case(ep, tx, tgold.get(tx["transaction_id"]) or {})
        states = [{"turn_id": s["turn_id"], "state": s["state"]} for s in fn]
        o = A.run_arms(case, states, nli=nli, gold=None, m1_llm=m1_llm)
        eg = egold.get(tx["episode_id"])
        if eg:
            env = A.Env(case)
            gm = A.ledger_to_mandate(gold_ctx(eg, {c["sku"]: c for c in ep["catalog"]}), case.reg, case.seller,
                                     f"m-{case.episode_id}", 1, env.session)
            d_, c_ = env.full_gate(gm)
            o["U_reference"] = {"decision": A.verdict.integrated(d_, c_, False), "codes": c_}
        g = tgold.get(tx["transaction_id"]) or {}
        rows.append({"transaction_id": tx["transaction_id"], "episode_id": tx["episode_id"],
                     "transaction_type": g.get("transaction_type"), "expected": g.get("expected_checkout"),
                     "context_violation": g.get("context_violation"), "authority_violation": g.get("authority_violation"),
                     "authority_check_codes": authority_check(tx), **o,
                     "fnctod_states": states, "plain_state": pl["state"]})
    (OUT / f"rows_{tag}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in rows),
                                           encoding="utf-8", newline="\n")
    n_matched = 0
    if a.with_matched:                               # separate analysis view; never merged into the main table
        mg = {g["challenge_id"]: g for g in jl(d / "matched_stockout_gold.jsonl")}
        mrows = []
        for mx in jl(d / "matched_stockout.jsonl"):
            v = ext.get(mx["episode_id"])
            if v is None or isinstance(v, Exception):
                continue
            fn, pl = v
            case = build_case(eps[mx["episode_id"]], mx, {})
            o = A.run_arms(case, [{"turn_id": s_["turn_id"], "state": s_["state"]} for s_ in fn], nli=nli, gold=None, m1_llm=m1_llm)
            g = mg.get(mx["challenge_id"]) or {}
            mrows.append({"challenge_id": mx["challenge_id"], "pair_id": mx["pair_id"], "episode_id": mx["episode_id"],
                          **{k: g.get(k) for k in ("intent_case", "reference_verdict", "evidence_status", "pair_similarity",
                                                    "analysis_stratum", "seller_claim_present")},
                          "arms": {k: {"decision": x["decision"], "codes": x["codes"]} for k, x in o["arms"].items()},
                          "e2_fires": o["e2_fires"]})
        (OUT / f"rows_{tag}_matched.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in mrows),
                                                       encoding="utf-8", newline="\n")
        n_matched = len(mrows)
    tab = defaultdict(Counter)
    for r in rows:
        for arm in r["arms"]:                         # B0-B4 and the added AV0-AV2 (docs/COMPARISON_ARMS_20261126.md)
            tab[(arm, r["transaction_type"], r["expected"])][r["arms"][arm]["decision"]] += 1
    summ.update({"failed": failed, "cost_usd": round(sum(sum(s.get("cost_usd", 0) for s in ext[e][0]) + ext[e][1]["cost_usd"]
                                                        for e in ext if not isinstance(ext[e], Exception)), 6),
                 "cache_hits": llm.cache_hits, "matched_rows": n_matched, "m1_main": "M1-G" if m1_llm else "rules_v2",
                 "m1g_cost_usd": round(m1_llm.spent, 6) if m1_llm else 0.0, "unverified_policy": A.UNVERIFIED_POLICY,
                 "m1g_memo": bool(a.m1g_memo), "ledger_tag": a.ledger_tag,
                 "m1g_requests_before_reuse": getattr(m1_llm, "requested", None),
                 "m1g_distinct_requests": getattr(m1_llm, "distinct", None),
                 "m1g_prewarm_errors": locals().get("prewarm_errors"),
                 "by_arm_type_expected": {f"{k[0]}|{k[1]}|{k[2]}": dict(v) for k, v in sorted(tab.items())}})
    (OUT / f"summary_{tag}.json").write_text(json.dumps(summ, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in summ.items() if k != "by_arm_type_expected"}))


if __name__ == "__main__":
    main()
