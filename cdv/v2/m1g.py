"""M1-G: M1 variant whose basis judgement is made by an LLM (researcher decision 2026-11-26).

Source rule unchanged and model-free: a change whose cited turn is not a user turn is REJECTED without a call.
Basis judgement: one user turn + the change candidate in plain words -> gpt-6-luna (reasoning low) classifies the
turn as one of
  decision        the user states the change as their decision            -> ACCEPT
  question        the user asks about it / supposes it / considers it      -> REJECT
  ambiguous       it could be read as the change or not                    -> CLARIFY
  not_mentioned   the turn does not state this change                      -> REJECT
An unparsable answer is CLARIFY (conservative) and counted. The prompt text is fixed and hashed (PROMPT_SHA256).
"""
from __future__ import annotations

import hashlib
import json
import re

SYSTEM = ("You check whether a shopper's message states a change to their purchase conditions. "
          "Answer with JSON only: {\"label\": \"decision\" | \"question\" | \"ambiguous\" | \"not_mentioned\"}.")
USER_TEMPLATE = (
    "Shopper message:\n{turn}\n\n"
    "Proposed change to the shopper's purchase conditions:\n{change}\n\n"
    "Labels:\n"
    "- decision: the shopper states this change as their own decision or instruction.\n"
    "- question: the shopper only asks about it, supposes it, or says they might consider it.\n"
    "- ambiguous: the message could be read either as making this change or not.\n"
    "- not_mentioned: the message does not state this change.\n"
    "Judge only this message. Do not assume anything that is not written in it.")
PROMPT_SHA256 = hashlib.sha256((SYSTEM + "\n---\n" + USER_TEMPLATE).encode("utf-8")).hexdigest()
LABEL_TO_DECISION = {"decision": "ACCEPT", "question": "REJECT", "ambiguous": "CLARIFY", "not_mentioned": "REJECT"}


def describe(op: dict, catalog: dict) -> str:
    """Plain-language change candidate (v4 operation format)."""
    f, o, v = op["field"], op["operation"], op.get("value")
    title = lambda s: (catalog.get(s) or {}).get("title") or str(s)  # noqa: E731
    if o == "REVOKE" or v in (None, {}, []):
        return {"Price": "Remove the spending limit.", "Deadline": "Remove the time limit.",
                "Fulfillment": "Remove the delivery or pickup requirement.", "Brand": "Remove the brand requirement.",
                "Attribute": "Remove the product attribute requirement.", "Quantity": "Remove the quantity requirement.",
                "Bundle": "Remove the requirement to buy the items together.",
                "Substitution": "Remove the substitution permission."}.get(f, f"Remove the {f} condition.")
    if f == "Price":
        return f"Set the total spending limit to USD {v / 100:.2f}."
    if f == "Deadline":
        return f"Require the order within {int(v)} days."
    if f == "Fulfillment":
        return "Change fulfillment to " + ("home delivery." if v == "delivery" else "store pickup.")
    if f == "Brand":
        inc, exc = v.get("include") or [], v.get("exclude") or []
        parts = ([f"allow only the brand(s) {', '.join(inc)}"] if inc else []) + ([f"exclude the brand(s) {', '.join(exc)}"] if exc else [])
        return "Brand condition: " + "; ".join(parts) + "."
    if f == "Quantity":
        return "Set the quantities to: " + "; ".join(f"{title(s)} x {n}" for s, n in v.items()) + "."
    if f == "Bundle":
        return "Buy these items together: " + "; ".join(title(s) for s in v) + "."
    if f == "Product":
        return "Switch the chosen product to: " + "; ".join(title(s) for s in v) + "."
    if f == "Substitution":
        return "; ".join(f"If {title(a)} is out of stock, substitute {title(b)}" for a, b in v.items()) + "."
    if f == "Attribute":
        return "Require these product attributes: " + json.dumps(v, ensure_ascii=False) + "."
    return f"{o} {f}: {json.dumps(v, ensure_ascii=False)}"


def parse(text: str) -> str | None:
    m = re.search(r"\{.*?\}", text or "", re.S)
    if not m:
        return None
    try:
        lab = json.loads(m.group(0)).get("label")
    except (json.JSONDecodeError, AttributeError):
        return None
    return lab if lab in LABEL_TO_DECISION else None


def decide(llm, op: dict, cited_role: str | None, user_text: str | None, catalog: dict):
    """Returns (decision, label, cost_usd). No call for a non-user cited turn."""
    if cited_role != "user" or user_text is None:
        return "REJECT", "non_user_source", 0.0
    r = llm(SYSTEM, USER_TEMPLATE.format(turn=user_text, change=describe(op, catalog)))
    lab = parse(r.text)
    if lab is None:
        return "CLARIFY", "unparsed", r.cost_usd
    return LABEL_TO_DECISION[lab], lab, r.cost_usd
