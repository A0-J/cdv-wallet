"""Condition extractors (untrusted): FnCTOD-style function-calling DST and a plain-LLM baseline.

FnCTOD (Li et al., ACL 2024, arXiv 2402.10466) re-implemented from the paper for the purchase domain.
The official code (github.com/facebookresearch/FnCTOD) is CC BY-NC 4.0 and is NOT copied here; this
follows the method as described in the paper:
  * each domain schema is a function; slot values are its arguments (sec. 4, Fig. 3)
  * two steps per user turn: function selection -> argument generation (sec. 4 "Function Call
    Decomposition"), the second step seeing only the selected function's full specification
  * previous turns' function calls are kept in the dialogue context ("w/ prev", Fig. 5)
  * the call carries the cumulative state of that function (Fig. 4)
Deviations (stated): purchase-domain schema written by us; the selection step may return more than one
function (a shopping turn can touch conditions and substitution at once); zero-shot (no examples).

The plain baseline reads the whole conversation once and returns JSON conditions (no function specs,
no decomposition, no per-turn state).

Providers: OpenAIResponses (key from OPENAI_API_KEY only; never printed or stored) and ScriptedLLM (tests).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

FUNCTIONS = [
    {"name": "set_purchase_conditions",
     "description": "the shopper's conditions for what to buy and how to receive it",
     "arguments": [
         {"name": "budget_max", "type": "number", "description": "maximum total price the shopper will pay, in the shopper's currency"},
         {"name": "quantity", "type": "integer", "description": "total number of units to buy"},
         {"name": "product_type", "type": "string", "description": "kind of product wanted"},
         {"name": "brand_include", "type": "array", "description": "brands the shopper requires"},
         {"name": "brand_exclude", "type": "array", "description": "brands the shopper refuses"},
         {"name": "required_items", "type": "array", "description": "items that must ALL be bought together (a bundle), by name"},
         {"name": "deadline_days", "type": "integer", "description": "latest acceptable delivery, in days"},
         {"name": "fulfillment", "type": "string", "description": "how to receive the order", "possible_values": ["pickup", "ship"]},
     ]},
    {"name": "set_substitution_policy",
     "description": "whether and how the shopper allows a substitute if the wanted item is unavailable",
     "arguments": [
         {"name": "allowed", "type": "boolean", "description": "true only if the shopper allows a substitute"},
         {"name": "scope", "type": "string", "description": "closest = most similar item; named = only the named alternatives", "possible_values": ["closest", "named"]},
         {"name": "named_alternatives", "type": "array", "description": "alternatives the shopper named"},
     ]},
]
FN_BY_NAME = {f["name"]: f for f in FUNCTIONS}
SYSTEM = ("You are a task-oriented shopping assistant. You can use the given functions to record the shopper's "
          "purchase conditions.")
CALL_FORMAT = ('To call a function, output <function_call> {"function": "function_name", "arguments": '
               '{"argument1": "value", ...}} </function_call>.')


@dataclass
class Turn:
    role: str          # "user" | "assistant"
    text: str
    turn_id: str = ""


@dataclass
class LLMResult:
    text: str
    usage: dict = field(default_factory=dict)
    latency_s: float = 0.0
    cost_usd: float = 0.0
    model: str = ""


# ---------------------------------------------------------------- providers

PRICES = {"gpt-6-luna": {"input": 0.10, "output": 0.50}, "gpt-6.1-sol": {"input": 2.00, "output": 10.00}}


class OpenAIResponses:
    """Responses API over urllib. Key from OPENAI_API_KEY only. Every call is appended to a JSONL ledger
    (request sha256, usage, cost, latency; never the key). Stops when the budget would be exceeded."""

    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, model: str, ledger: Path, budget_usd: float, max_output_tokens: int = 2000,
                 reasoning_effort: str = "low", timeout: float = 120.0):
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            raise SystemExit("OPENAI_API_KEY is not set. Nothing was sent.")
        if model not in PRICES:
            raise SystemExit(f"no price recorded for {model}")
        self._key, self.model, self.ledger = key, model, Path(ledger)
        self.budget, self.max_out, self.effort, self.timeout = budget_usd, max_output_tokens, reasoning_effort, timeout
        self.spent = self._spent_so_far()

    def _spent_so_far(self) -> float:
        if not self.ledger.exists():
            return 0.0
        return sum(json.loads(l).get("cost_usd", 0.0) for l in self.ledger.read_text(encoding="utf-8").splitlines() if l)

    def worst_case(self, n_input_tokens: int) -> float:
        p = PRICES[self.model]
        return (n_input_tokens * p["input"] + self.max_out * p["output"]) / 1e6

    def __call__(self, system: str, user: str) -> LLMResult:
        import urllib.error
        import urllib.request
        body = json.dumps({"model": self.model, "input": [{"role": "system", "content": system},
                                                          {"role": "user", "content": user}],
                           "reasoning": {"effort": self.effort}, "max_output_tokens": self.max_out}).encode("utf-8")
        est_in = len(body) // 3
        if self.spent + self.worst_case(est_in) > self.budget:
            raise SystemExit(f"budget stop: spent {self.spent:.4f} + worst case would exceed {self.budget}")
        rq = urllib.request.Request(self.endpoint, data=body, method="POST",
                                    headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"})
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(rq, timeout=self.timeout) as r:  # noqa: S310
                resp = json.loads(r.read().decode("utf-8"))
            err = None
        except urllib.error.HTTPError as e:
            resp, err = {}, f"http {e.code}"
        lat = time.perf_counter() - t0
        u = resp.get("usage") or {}
        p = PRICES[self.model]
        cost = (u.get("input_tokens", 0) * p["input"] + u.get("output_tokens", 0) * p["output"]) / 1e6
        self.spent += cost
        text = "".join(c.get("text", "") for o in resp.get("output", []) if o.get("type") == "message"
                       for c in o.get("content", []) if c.get("type") == "output_text")
        rec = {"ts": time.time(), "model": resp.get("model", self.model), "request_sha256": hashlib.sha256(body).hexdigest(),
               "usage": u, "cost_usd": round(cost, 8), "latency_s": round(lat, 3), "error": err,
               "status": resp.get("status"), "output_text": text}
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if err:
            raise RuntimeError(err)
        return LLMResult(text, u, lat, cost, resp.get("model", self.model))


class ScriptedLLM:
    """Test double: returns queued strings (no network)."""

    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def __call__(self, system: str, user: str) -> LLMResult:
        self.calls.append((system, user))
        return LLMResult(self.replies.pop(0) if self.replies else "<domain>none</domain>")


# ---------------------------------------------------------------- FnCTOD

def _render(context: list[Turn], prev_calls: dict[int, list[dict]]) -> str:
    lines = []
    for i, t in enumerate(context):
        if t.role == "user":
            lines.append(f"User: {t.text}")
        else:
            calls = "".join(f"<function_call> {json.dumps(c, ensure_ascii=False)} </function_call> "
                            for c in prev_calls.get(i, []))
            lines.append(f"Assistant: {calls}{t.text[:400]}")
    return "\n".join(lines)


def _parse_calls(text: str) -> list[dict]:
    out = []
    for m in re.finditer(r"<function_call>\s*(\{.*?\})\s*</function_call>", text, re.S):
        try:
            c = json.loads(m.group(1))
            if c.get("function") in FN_BY_NAME and isinstance(c.get("arguments"), dict):
                out.append(c)
        except json.JSONDecodeError:
            continue
    return out


class FnCTOD:
    """Per user turn: step 1 selects functions, step 2 generates cumulative arguments for each."""

    def __init__(self, llm):
        self.llm = llm

    def run(self, dialogue: list[Turn]) -> list[dict]:
        """Returns, per user turn, {'turn_index', 'state': {fn: args}, 'selected', 'calls', 'latency_s', 'cost_usd'}."""
        state: dict[str, dict] = {}
        prev_calls: dict[int, list[dict]] = {}
        out = []
        for i, t in enumerate(dialogue):
            if t.role != "user":
                continue
            ctx = _render(dialogue[: i + 1], prev_calls)
            brief = "\n".join(f"- {f['name']}: {f['description']}" for f in FUNCTIONS)
            sel_sys = f"{SYSTEM}\n<FUNCTIONS>\n{brief}\n</FUNCTIONS>"
            sel_user = (f"{ctx}\n\nFor the LAST user turn only: which functions' arguments does it set or change? "
                        "Answer with one <domain>function_name</domain> per line, or <domain>none</domain>.")
            r1 = self.llm(sel_sys, sel_user)
            selected = [s for s in re.findall(r"<domain>\s*([\w_]+)\s*</domain>", r1.text) if s in FN_BY_NAME]
            lat, cost, calls = r1.latency_s, r1.cost_usd, []
            for fn in selected:
                spec = json.dumps(FN_BY_NAME[fn], ensure_ascii=False, indent=1)
                arg_sys = f"{SYSTEM}\n<FUNCTIONS>\n{spec}\n</FUNCTIONS>\n{CALL_FORMAT}"
                prev = state.get(fn)
                arg_user = (f"{ctx}\n\nCurrent recorded call: {json.dumps({'function': fn, 'arguments': prev or {}})}\n"
                            f"Output the {fn} call with the shopper's CURRENT conditions after the last user turn "
                            "(cumulative). Include only arguments the shopper has stated.")
                r2 = self.llm(arg_sys, arg_user)
                lat += r2.latency_s
                cost += r2.cost_usd
                for c in _parse_calls(r2.text):
                    if c["function"] == fn:
                        state[fn] = c["arguments"]
                        calls.append(c)
            prev_calls[i] = calls
            out.append({"turn_index": i, "turn_id": t.turn_id, "selected": selected, "calls": calls,
                        "state": json.loads(json.dumps(state)), "latency_s": round(lat, 3), "cost_usd": cost})
        return out


class PlainLLM:
    """Baseline: one call over the whole conversation, JSON out, same argument names."""

    def __init__(self, llm):
        self.llm = llm

    def run(self, dialogue: list[Turn]) -> dict:
        ctx = "\n".join(f"{'User' if t.role == 'user' else 'Assistant'}: {t.text[:400]}" for t in dialogue)
        keys = [a["name"] for f in FUNCTIONS for a in f["arguments"]]
        sys_ = "Read the shopping conversation and extract the shopper's current purchase conditions."
        usr = (f"{ctx}\n\nReturn one JSON object with any of these keys the shopper has stated: {', '.join(keys)}. "
               "Use substitution keys allowed/scope/named_alternatives only if the shopper talked about substitutes.")
        r = self.llm(sys_, usr)
        m = re.search(r"\{.*\}", r.text, re.S)
        try:
            flat = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            flat = {}
        pc = {k: v for k, v in flat.items() if k in [a["name"] for a in FUNCTIONS[0]["arguments"]]}
        sp = {k: v for k, v in flat.items() if k in [a["name"] for a in FUNCTIONS[1]["arguments"]]}
        state = {}
        if pc:
            state["set_purchase_conditions"] = pc
        if sp:
            state["set_substitution_policy"] = sp
        return {"state": state, "latency_s": r.latency_s, "cost_usd": r.cost_usd}
