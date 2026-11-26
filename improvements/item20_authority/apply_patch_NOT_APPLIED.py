"""Adjustment-history item 20 (researcher decision 2026-11-27, v4b not opened): payment-request authority check moved
from the evaluation script into the system (cdv/authority.py) and applied before the gate to every configuration that
checks at payment time. Apply ONLY after R-v4g condition B has started (its process must keep the 610a97c code)."""
import shutil
from pathlib import Path

ROOT = Path(r"C:\agentic-wallet-security\cdv-wallet")
BK = Path(r"C:\Users\user\AppData\Local\Temp\claude\0278563a286f53dd\5e865646-3894-4001-8edb-e450d3c47fd7\scratchpad\pre_item20")
BK.mkdir(exist_ok=True)


def patch(rel, reps):
    p = ROOT / rel
    shutil.copy(p, BK / p.name)
    s = p.read_text(encoding="utf-8")
    for old, new in reps:
        assert s.count(old) == 1, (rel, old[:80])
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8", newline="\n")
    print("patched", rel)


patch("eval/integrated/arms.py", [
    ("from cdv import verdict  # noqa: E402\n", "from cdv import authority as AUTH  # noqa: E402\nfrom cdv import verdict  # noqa: E402\n"),
    ("def run_arms(case, states: list, nli=None, gold: dict | None = None, m1_llm=None) -> dict:",
     "def run_arms(case, states: list, nli=None, gold: dict | None = None, m1_llm=None, authority_codes: list | None = None) -> dict:"),
    ('''    out["e2_fires"] = env.e2
    out["n_offers"] = len(case.offers)
    return out''', '''    out["e2_fires"] = env.e2
    out["n_offers"] = len(case.offers)
    # adjustment 20 (2026-11-27): payment-request authority check (cdv/authority.py) before the gate, the same for every
    # configuration that checks at payment time. B0 (the no-check floor) and the U reference are left as they are.
    # authority_codes come from cdv.authority.check_payment_authority on the payment request and its grant (none in
    # CartTrace -> nothing changes). The decision without it is kept as 'pre_authority'.
    out["authority_codes"] = list(authority_codes or [])
    if authority_codes:
        for name, a in out["arms"].items():
            if name == "B0":
                continue
            a["pre_authority"] = a["decision"]
            a["decision"], a["codes"] = AUTH.apply(a["decision"], a["codes"], authority_codes)
    return out'''),
])

patch("eval/extdata/run_ext.py", [
    ('''def authority_check(tx: dict) -> list:
    """Separate axis: payment request against its grant (never merged into the main decision)."""''',
     '''def authority_check(tx: dict) -> list:
    """Payment request against its grant. Since adjustment 20 (2026-11-27) this is the system check
    cdv/authority.py::check_payment_authority, applied before the gate to every configuration (run_arms); the old
    evaluation-script comparison below is kept only to assert that the two give the same codes."""
    from cdv.authority import check_payment_authority
    sys_codes = check_payment_authority(tx.get("payment_request"), tx.get("payment_grant"))
    assert sys_codes == _authority_check_script(tx), "system authority check differs from the evaluation-script check"
    return sys_codes


def _authority_check_script(tx: dict) -> list:
    """The evaluation-script comparison used before adjustment 20 (unchanged)."""'''),
    ('''        o = A.run_arms(case, states, nli=nli, gold=None, m1_llm=m1_llm)''',
     '''        o = A.run_arms(case, states, nli=nli, gold=None, m1_llm=m1_llm, authority_codes=authority_check(tx))'''),
    ('''            o = A.run_arms(case, [{"turn_id": s_["turn_id"], "state": s_["state"]} for s_ in fn], nli=nli, gold=None, m1_llm=m1_llm)''',
     '''            o = A.run_arms(case, [{"turn_id": s_["turn_id"], "state": s_["state"]} for s_ in fn], nli=nli, gold=None, m1_llm=m1_llm,
                           authority_codes=authority_check(mx))'''),
])

patch("eval/extdata/run_baselines.py", [
    ('''from cdv import verdict  # noqa: E402''', '''from cdv import authority as AUTH  # noqa: E402
from cdv import verdict  # noqa: E402'''),
    ('''        key = (kind, g.get("transaction_type") or g.get("intent_case"), g.get("expected_checkout") or g.get("reference_verdict"))''',
     '''        # adjustment 20: the payment-request authority check before the decision, same as every gate configuration
        auth = AUTH.check_payment_authority(tx.get("payment_request"), tx.get("payment_grant"))
        pre_auth = (p[0], sdec)
        p = (AUTH.apply(p[0], [], auth)[0],) + tuple(p[1:])
        if sdec is not None:
            sdec = AUTH.apply(sdec, [], auth)[0]
        key = (kind, g.get("transaction_type") or g.get("intent_case"), g.get("expected_checkout") or g.get("reference_verdict"))'''),
    ('''                     "type": key[1], "expected": key[2], "precheck": p[0], "precheck_unparsed": p[1], "summary": sdec,''',
     '''                     "type": key[1], "expected": key[2], "precheck": p[0], "precheck_unparsed": p[1], "summary": sdec,
                     "authority_codes": auth, "precheck_pre_authority": pre_auth[0], "summary_pre_authority": pre_auth[1],'''),
])
