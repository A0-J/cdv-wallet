"""LLM baselines for the integrated comparison (prompts fixed and hashed; not run without plan approval).

PRECHECK  "pre-payment re-check": the model reads the dialogue before the decision point and the payment request
          (cart lines, fees, fulfillment, days) and answers allow / block / clarify. No ledger, no mandate.
SUMMARY   "summary baseline": the model summarises the shopper's purchase conditions from the dialogue; the plain
          extractor (cdv/extract.py::PlainLLM, unchanged) reads that summary; the result becomes a mandate checked by
          the full M2 gate (same as B2 but the conditions come from a summary instead of the dialogue).
"""
from __future__ import annotations

import hashlib
import json
import re

PRECHECK_SYSTEM = ("You review an online purchase before payment on behalf of the shopper. "
                   "Answer with JSON only: {\"decision\": \"allow\" | \"block\" | \"clarify\"}.")
PRECHECK_USER = (
    "Conversation between the shopper and the shopping agent (oldest first):\n{dialogue}\n\n"
    "Payment request:\n{cart}\n\n"
    "Decide:\n- allow: the payment request matches what the shopper decided.\n"
    "- block: the payment request breaks a condition the shopper decided.\n"
    "- clarify: it is unclear whether the shopper would accept this payment request.\n"
    "Only the shopper's own words set conditions. Statements by the agent, a seller or a store are not the shopper's decisions.")
SUMMARY_SYSTEM = "You summarise a shopping conversation. Answer in plain English, at most 8 short sentences."
SUMMARY_USER = (
    "Conversation between the shopper and the shopping agent (oldest first):\n{dialogue}\n\n"
    "Write the shopper's current purchase conditions as decided by the shopper: items and quantities, budget, brands, "
    "delivery or pickup, time limit, and whether substitutes are allowed. Leave out anything the shopper did not decide.")
PROMPTS_SHA256 = hashlib.sha256("\n---\n".join([PRECHECK_SYSTEM, PRECHECK_USER, SUMMARY_SYSTEM, SUMMARY_USER]).encode("utf-8")).hexdigest()
PRECHECK_TO_DECISION = {"allow": "ALLOW", "block": "DENY", "clarify": "CLARIFY"}


def dialogue_text(turns) -> str:
    """turns: iterable of (speaker, text) with speaker in {'shopper', 'agent'}."""
    return "\n".join(f"{s}: {t}" for s, t in turns)


def cart_text(lines, fees: float | None = None, fulfillment: str | None = None, days: int | None = None) -> str:
    out = [f"- {l['title']} | brand: {l.get('brand') or 'unknown'} | unit price: {l['unit_price']:.2f} | quantity: {l['quantity']}" for l in lines]
    if fees is not None:
        out.append(f"- fees and shipping: {fees:.2f}")
    if fulfillment:
        out.append(f"- fulfillment: {fulfillment}")
    if days is not None:
        out.append(f"- ready within: {days} days")
    return "\n".join(out)


def precheck(llm, turns, lines, **kw):
    r = llm(PRECHECK_SYSTEM, PRECHECK_USER.format(dialogue=dialogue_text(turns), cart=cart_text(lines, **kw)))
    m = re.search(r"\{.*?\}", r.text or "", re.S)
    try:
        lab = json.loads(m.group(0)).get("decision") if m else None
    except json.JSONDecodeError:
        lab = None
    return PRECHECK_TO_DECISION.get(lab, "CLARIFY"), lab is None, r.cost_usd


def summarize(llm, turns):
    r = llm(SUMMARY_SYSTEM, SUMMARY_USER.format(dialogue=dialogue_text(turns)))
    return (r.text or "").strip(), r.cost_usd
