"""E-M1: FnCTOD extraction + M1 verification on real CartTrace dialogues (and G1, reported separately).

Arms share one extraction per journey (plain-LLM output is a separate extraction):
  plain | fnctod | fnctod_r (rules) | fnctod_rn (rules + NLI) ; upper bound U = gold ledger (reported apart)
Gold (hidden spec) is used ONLY for scoring and for U; it is never an input of any arm.

Usage
  dry run (no network; real prompt sizes -> cost estimate):
    .venv/Scripts/python.exe eval/e_m1/run.py --set R1 --split test_cross_store --n 200 --dry-run
  live (after plan approval; OPENAI_API_KEY in env):
    .venv/Scripts/python.exe eval/e_m1/run.py --set R1 ... --model gpt-6-luna --budget 15
"""
from __future__ import annotations

import argparse
import glob
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cdv import m1  # noqa: E402
from cdv.extract import FnCTOD, LLMResult, OpenAIResponses, PlainLLM, Turn  # noqa: E402
from cdv.m1 import Entry, Ledger, UserTurn  # noqa: E402
from cdv.pipeline import cart_check, run_verified, state_to_entries  # noqa: E402

DATA = Path(r"C:/ct/kit/dataset/data")
OUT = ROOT / "results" / "e_m1_20261126"
SEED = 20261127
PICK = re.compile(r"(i.ll go with|i will proceed with|go with option|option \d|i.d rather|i.ll take|let.s go with|that one)", re.I)
DECL = re.compile(r"(not (the item|what) i (asked|requested|wanted)|isn.t what i asked|don.t place|do not place|stop the order|refrain from placing|cancel (the|my) order|don.t (want|proceed)|hold off|decline)", re.I)
LEGIT, VIOL = {"RIGHT", "RIGHT_BY_LUCK"}, {"WRONG", "WRONG_HIDDEN"}


class DryLLM:
    """No network. Records prompt sizes; returns empty answers (wiring and cost estimate only)."""

    def __init__(self):
        self.chars_in = 0
        self.calls = 0

    def __call__(self, system, user):
        self.calls += 1
        self.chars_in += len(system) + len(user)
        return LLMResult("<domain>none</domain>" if "<domain>" in user else "{}")


# ---------------------------------------------------------------- data

def load_messages(splits):
    cols = ["episode_id", "hidden_spec", "kind", "sub_kind", "outcome_class", "final_cart", "template_family", "split"]
    rows = []
    for s in splits:
        for f in sorted(glob.glob(str(DATA / "messages" / "*" / f"{s}-*.parquet"))):
            rows += pq.read_table(f, columns=cols).to_pylist()
    return rows


def load_dialogues(eids: set, splits):
    turns = defaultdict(list)
    for s in splits:
        for f in sorted(glob.glob(str(DATA / "turns" / f"{s}-*.parquet"))):
            for x in pq.read_table(f, columns=["episode_id", "seq", "actor", "kind", "text"]).to_pylist():
                if x["episode_id"] in eids and x["kind"] == "message" and (x["text"] or "").strip() and x["actor"] in ("shopper", "agent"):
                    turns[x["episode_id"]].append(x)
    return {e: sorted(v, key=lambda z: z["seq"]) for e, v in turns.items()}


def gold_fields(h: dict) -> dict:
    g = {}
    for p in h.get("predicates") or []:
        src, op, v = p.get("source"), p.get("op"), p.get("value")
        if src not in ("stated", "on_ask"):
            continue
        if op == "max_price" and isinstance(v, dict):
            g["budget_max"] = (v["amount"] / 100, src)
        elif op == "count":
            try:
                g["quantity"] = (int(v), src)
            except (TypeError, ValueError):
                pass
        elif op == "all_of" and isinstance(v, list):
            g["bundle_all"] = (len(v), src)
        elif op == "brand":
            g["brand_in"] = (str(v).lower(), src)
        elif op == "excludes":
            g["brand_out"] = (str(v).lower(), src)
        elif op == "prefer":
            g["substitute"] = (True, src)
    f = (h.get("buyer") or {}).get("fulfillment") or {}
    if f.get("source") in ("stated", "on_ask"):
        g["fulfillment"] = ("pickup" if f.get("value") == "pickup" else "ship", f["source"])
        if f.get("deadline_days"):
            g["deadline_days"] = (int(f["deadline_days"]), f["source"])
    return g


def entry_correct(e: Entry, g: dict) -> bool | None:
    """True/False against gold; None if not scorable (product_type)."""
    f = e.field
    if f == "product_type":
        return None
    if f not in g:
        return False                      # unfounded condition (not in the shopper's spec)
    gv = g[f][0]
    if f == "budget_max":
        return abs(float(e.value) - gv) <= max(1.0, 0.01 * gv)
    if f in ("quantity", "deadline_days"):
        return int(e.value) == gv
    if f == "bundle_all":
        return len(e.value) == gv
    if f in ("brand_in", "brand_out"):
        return any(gv in str(x).lower() or str(x).lower() in gv for x in e.value)
    if f == "fulfillment":
        return e.value == gv
    if f == "substitute":
        return True
    return None


def cart_lines(final_cart: str):
    try:
        c = json.loads(final_cart or "{}")
    except json.JSONDecodeError:
        return []
    return [{"title": l.get("title") or "", "unit_price": (l.get("unit_price") or 0) / 100, "quantity": l.get("quantity") or 1}
            for l in c.get("lines") or []]


def select(set_name, split, n, rows, dialogs_needed=True):
    rng = random.Random(SEED)
    base = [r for r in rows if r["kind"] == "baseline" and r["outcome_class"] in LEGIT | VIOL and cart_lines(r["final_cart"])]
    if set_name == "R1":
        pool = [r for r in base if any(k != "substitute" for k in gold_fields(json.loads(r["hidden_spec"])))]
    elif set_name == "R3":
        pool = [r for r in base if any(f.get("kind") == "stockout" for f in json.loads(r["hidden_spec"]).get("faults") or [])]
    else:
        raise SystemExit("R2 is selected in main() from dialogue text")
    pool.sort(key=lambda r: r["episode_id"])
    return rng.sample(pool, min(n, len(pool)))


# ---------------------------------------------------------------- per journey

def run_journey(r, dlg, fn_llm, plain_llm, nli):
    h = json.loads(r["hidden_spec"])
    g = gold_fields(h)
    dialogue = [Turn("user" if x["actor"] == "shopper" else "assistant", x["text"], f"s{x['seq']}") for x in dlg]
    user_turns = [UserTurn(f"s{x['seq']}", x["seq"], x["text"]) for x in dlg if x["actor"] == "shopper"]
    t0 = time.perf_counter()
    fn = FnCTOD(fn_llm).run(dialogue)
    t_fn = time.perf_counter() - t0
    pl = PlainLLM(plain_llm).run(dialogue)
    for st in fn:
        st["seq"] = int(st["turn_id"][1:])
    cart = cart_lines(r["final_cart"])
    final_fn = fn[-1]["state"] if fn else {}
    arms = {}
    for name, state in (("plain", pl["state"]), ("fnctod", final_fn)):
        led = Ledger(1, tuple(state_to_entries(state).values()))
        d, codes = cart_check(led, cart)
        arms[name] = {"ledger": led, "hint": "OK", "decision": d, "codes": codes, "flags": [], "verify_ms": 0.0,
                      "proposed": list(led.entries)}
    brands = sorted({str(b) for st in fn for k in ("brand_include", "brand_exclude")
                     for b in ((st["state"].get("set_purchase_conditions") or {}).get(k) or [])})
    for name, use_nli in (("fnctod_r", None), ("fnctod_rn", nli)):
        res = run_verified(fn, user_turns, nli=use_nli, known_brands=brands)
        d, codes = cart_check(res["ledger"], cart)
        arms[name] = {"ledger": res["ledger"], "hint": res["hint"], "decision": "CLARIFY" if res["hint"] == "CLARIFY" else d,
                      "codes": codes, "flags": res["flags"], "verify_ms": res["verify_ms"],
                      "proposed": list(state_to_entries(final_fn).values()), "trace": res["trace"]}
    gold_led = Ledger(1, tuple(Entry(f"g_{k}", k, (v if k not in ("brand_in", "brand_out") else (v,)) if k != "bundle_all" else tuple(range(v)))
                               for k, (v, _) in g.items() if k != "substitute"))
    du, _ = cart_check(gold_led, cart)
    out = {"episode_id": r["episode_id"], "outcome": r["outcome_class"], "gold": {k: v for k, v in g.items()},
           "n_user_turns": len(user_turns), "extract_s": round(t_fn, 3),
           "cost_usd": round(sum(s["cost_usd"] for s in fn) + pl["cost_usd"], 6), "upper_bound_decision": du, "arms": {}}
    stated = {k for k, (_, s) in g.items() if s == "stated"}
    for name, a in arms.items():
        acc = {e.field: e for e in a["ledger"].entries}
        prop = a["proposed"]
        sc = [(e, entry_correct(e, g)) for e in prop]
        omitted_flag = {c.split(":")[0] for c in a["flags"] if c.startswith("OMITTED_")}
        miss = [k for k in stated if k not in acc]
        out["arms"][name] = {
            "decision": a["decision"], "hint": a["hint"], "codes": a["codes"], "flags": a["flags"], "verify_ms": a["verify_ms"],
            "proposed_correct": sum(1 for _, c in sc if c is True), "proposed_wrong": sum(1 for _, c in sc if c is False),
            "accepted_correct": sum(1 for e, c in sc if c is True and e.field in acc and acc[e.field].value == e.value),
            "accepted_wrong": sum(1 for e, c in sc if c is False and e.field in acc and acc[e.field].value == e.value),
            "stated_n": len(stated), "missing_stated": len(miss),
            "missing_silent": len(miss) if a["hint"] == "OK" else 0,
            "ledger": {e.field: (list(e.value) if isinstance(e.value, tuple) else e.value) for e in a["ledger"].entries}}
    return out


def summarize(rows):
    s = {}
    for name in ("plain", "fnctod", "fnctod_r", "fnctod_rn"):
        A = [r["arms"][name] for r in rows]
        pw, aw = sum(a["proposed_wrong"] for a in A), sum(a["accepted_wrong"] for a in A)
        pc, ac = sum(a["proposed_correct"] for a in A), sum(a["accepted_correct"] for a in A)
        st, ms = sum(a["stated_n"] for a in A), sum(a["missing_silent"] for a in A)
        legit = [r for r in rows if r["outcome"] in LEGIT]
        viol = [r for r in rows if r["outcome"] in VIOL]
        s[name] = {
            "unjustified_condition_detection_pct": round(100 * (1 - aw / pw), 1) if pw else None, "n_unjustified": pw,
            "legit_condition_acceptance_pct": round(100 * ac / pc, 1) if pc else None, "n_legit": pc,
            "silent_omission_pct": round(100 * ms / st, 1) if st else None, "n_stated": st,
            "clarify_pct": round(100 * sum(a["hint"] == "CLARIFY" for a in A) / len(A), 1),
            "legit_cart_blocked_pct": round(100 * sum(r["arms"][name]["decision"] != "ALLOW" for r in legit) / len(legit), 1) if legit else None,
            "violating_cart_allowed_pct": round(100 * sum(r["arms"][name]["decision"] == "ALLOW" for r in viol) / len(viol), 1) if viol else None,
            "n_legit_carts": len(legit), "n_violating_carts": len(viol),
            "verify_ms_median": sorted(a["verify_ms"] for a in A)[len(A) // 2]}
    legit = [r for r in rows if r["outcome"] in LEGIT]
    viol = [r for r in rows if r["outcome"] in VIOL]
    s["upper_bound_gold_ledger"] = {
        "legit_cart_blocked_pct": round(100 * sum(r["upper_bound_decision"] != "ALLOW" for r in legit) / len(legit), 1) if legit else None,
        "violating_cart_allowed_pct": round(100 * sum(r["upper_bound_decision"] == "ALLOW" for r in viol) / len(viol), 1) if viol else None}
    s["extract_s_median"] = sorted(r["extract_s"] for r in rows)[len(rows) // 2] if rows else None
    s["cost_usd_total"] = round(sum(r["cost_usd"] for r in rows), 4)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["R1", "R2", "R3"], required=True)
    ap.add_argument("--split", default="test_cross_store")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default="gpt-6-luna")
    ap.add_argument("--budget", type=float, default=15.0)
    ap.add_argument("--no-nli", action="store_true")
    a = ap.parse_args()
    splits = [a.split] if a.set != "R2" else ["train", "validation", "test_cross_store", "test_cross_template"]
    rows = load_messages(splits)
    if a.set == "R2":
        cand = {r["episode_id"]: r for r in rows if r["sub_kind"] == "checkout"
                or any(f.get("kind") == "stockout" for f in json.loads(r["hidden_spec"]).get("faults") or [])}
        dl = load_dialogues(set(cand), splits)
        chosen = []
        for e, d in dl.items():
            sh = [x for x in d if x["actor"] == "shopper"][1:]
            p = [i for i, x in enumerate(sh) if PICK.search(x["text"])]
            q = [i for i, x in enumerate(sh) if DECL.search(x["text"])]
            if p and q and min(p) < max(q) and cand[e]["outcome_class"] in LEGIT | VIOL and cart_lines(cand[e]["final_cart"]):
                chosen.append(cand[e])
        chosen.sort(key=lambda r: r["episode_id"])
        sample = chosen[: a.n]
    else:
        sample = select(a.set, a.split, a.n, rows)
        dl = load_dialogues({r["episode_id"] for r in sample}, splits)
    tag = f"{a.set}_{a.split}" + ("_dry" if a.dry_run else "")
    if a.dry_run:
        fn_llm, pl_llm = DryLLM(), DryLLM()
    else:
        ledger = OUT / "ledger.jsonl"
        fn_llm = pl_llm = OpenAIResponses(a.model, ledger, a.budget)
    nli = None
    if not a.no_nli:
        from cdv.nli import NLI
        nli = NLI()
    res = [run_journey(r, dl.get(r["episode_id"], []), fn_llm, pl_llm, nli) for r in sample if dl.get(r["episode_id"])]
    OUT.mkdir(parents=True, exist_ok=True)
    assert a.dry_run or not (OUT / f"rows_{tag}.jsonl").exists(), f"refusing to overwrite rows_{tag}.jsonl"
    (OUT / f"rows_{tag}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False, default=str) + "\n" for x in res),
                                           encoding="utf-8", newline="\n")
    summ = {"set": a.set, "split": a.split, "n": len(res), "model": None if a.dry_run else a.model,
            "dry_run": a.dry_run, "summary": summarize(res) if res else {}}
    if a.dry_run:
        tok = (fn_llm.chars_in + pl_llm.chars_in) / 4
        summ["dry_run_estimate"] = {"calls_lower_bound": fn_llm.calls + pl_llm.calls, "input_tokens_est": int(tok),
                                    "note": "dry answers select no function, so FnCTOD step-2 calls are not counted here"}
    (OUT / f"summary_{tag}.json").write_text(json.dumps(summ, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: summ[k] for k in ("set", "n")}), json.dumps(summ.get("dry_run_estimate")))




# ---------------------------------------------------------------- G1 (generated; reported separately)

G1_FILE = Path(r"C:/ct/runs/cdv_wallet/generated/G1/eval.jsonl")


def g1_expect(c):
    t = c["template_id"]
    prev = {e["field"]: e["value"] for e in c["prev_ledger"]["entries"]}
    last = c["user_turns"][-1]["text"]
    vals = m1.budget_mentions(last)
    if t in ("C1_relax_explicit", "C4_relax_value_mismatch", "X1_two_budgets_unresolved", "X2_budget_overridden",
             "O1_omitted_budget", "C5_tighten"):
        return {"budget_max": vals[-1] if vals else None}
    if t in ("C2_relax_no_cue", "C3_relax_seller_source", "C9_substitute_no_cue"):
        return {"budget_max": prev.get("budget_max"), "no_substitute": True}
    if t == "C6_ambiguous_pick_bundle":
        return {"bundle_kept_or_clarify": len(prev.get("bundle_all", []))}
    if t == "C7_explicit_drop_bundle":
        return {"bundle_dropped": True}
    if t == "C8_add_substitute":
        return {"substitute": True}
    if t == "X3_brand_in_out":
        return {"clarify": True}
    return {}


def g1_correct(exp, led: Ledger, hint: str) -> bool:
    by = {e.field: e.value for e in led.entries}
    ok = True
    if "budget_max" in exp and exp["budget_max"] is not None:
        ok &= "budget_max" in by and abs(float(by["budget_max"]) - float(exp["budget_max"])) <= 1
    if exp.get("no_substitute"):
        ok &= "substitute" not in by
    if "bundle_kept_or_clarify" in exp:
        ok &= hint == "CLARIFY" or len(by.get("bundle_all", ())) >= exp["bundle_kept_or_clarify"]
    if exp.get("bundle_dropped"):
        ok &= len(by.get("bundle_all", ())) <= 1
    if exp.get("substitute"):
        ok &= "substitute" in by
    if exp.get("clarify"):
        ok &= hint == "CLARIFY"
    return bool(ok)


def run_g1(fn_llm, plain_llm, nli, n):
    cases = [json.loads(l) for l in G1_FILE.read_text(encoding="utf-8").splitlines()][:n]
    out = []
    for c in cases:
        ut = [UserTurn(f"s{i * 2}", i * 2, u["text"]) for i, u in enumerate(c["user_turns"])]
        dialogue = [Turn("user", ut[0].text, ut[0].turn_id)]
        for x in c.get("external_texts") or []:
            dialogue.append(Turn("assistant", x["text"], "s1"))
        for u in ut[1:]:
            dialogue.append(Turn("user", u.text, u.turn_id))
        fn = FnCTOD(fn_llm).run(dialogue)
        for st in fn:
            st["seq"] = int(st["turn_id"][1:])
        pl = PlainLLM(plain_llm).run(dialogue)
        exp = g1_expect(c)
        row = {"case_id": c["case_id"], "template_id": c["template_id"], "arms": {}}
        for name, state in (("plain", pl["state"]), ("fnctod", fn[-1]["state"] if fn else {})):
            led = Ledger(1, tuple(state_to_entries(state).values()))
            row["arms"][name] = {"correct": g1_correct(exp, led, "OK"), "hint": "OK"}
        for name, use in (("fnctod_r", None), ("fnctod_rn", nli)):
            res = run_verified(fn, ut, nli=use)
            row["arms"][name] = {"correct": g1_correct(exp, res["ledger"], res["hint"]), "hint": res["hint"],
                                 "verify_ms": res["verify_ms"]}
        out.append(row)
    return out


def main_g1():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=260)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default="gpt-6-luna")
    ap.add_argument("--budget", type=float, default=15.0)
    ap.add_argument("--no-nli", action="store_true")
    a = ap.parse_args(sys.argv[2:])
    fn_llm = pl_llm = DryLLM() if a.dry_run else OpenAIResponses(a.model, OUT / "ledger.jsonl", a.budget)
    nli = None
    if not a.no_nli:
        from cdv.nli import NLI
        nli = NLI()
    rows = run_g1(fn_llm, pl_llm, nli, a.n)
    tag = "G1_eval" + ("_dry" if a.dry_run else "")
    assert a.dry_run or not (OUT / f"rows_{tag}.jsonl").exists(), f"refusing to overwrite rows_{tag}.jsonl"
    (OUT / f"rows_{tag}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="\n")
    by = defaultdict(lambda: defaultdict(Counter))
    for r in rows:
        for arm, v in r["arms"].items():
            by[arm][r["template_id"]]["n"] += 1
            by[arm][r["template_id"]]["correct"] += v["correct"]
    summ = {"set": "G1 (generated)", "n": len(rows), "dry_run": a.dry_run,
            "correct_pct": {arm: round(100 * sum(c["correct"] for c in t.values()) / sum(c["n"] for c in t.values()), 1)
                            for arm, t in by.items()},
            "by_template": {arm: {k: dict(v) for k, v in t.items()} for arm, t in by.items()}}
    if a.dry_run:
        summ["dry_run_estimate"] = {"calls_lower_bound": fn_llm.calls, "input_tokens_est": int(fn_llm.chars_in / 4)}
    (OUT / f"summary_{tag}.json").write_text(json.dumps(summ, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"n": len(rows), "correct_pct": summ["correct_pct"], "est": summ.get("dry_run_estimate")}))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "G1":
        main_g1()
    else:
        main()
