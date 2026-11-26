"""Ledger-only replay client (no network, no key): answers a request only if the same request body (same sha256 as
cdv/extract.py::OpenAIResponses builds) is in the ledger; otherwise counts a miss and raises (nothing is sent)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cdv.extract import LLMResult


class Replay:
    def __init__(self, ledger, model="gpt-6-luna", effort="low", max_out=2000):
        self.cache = {}
        for l in Path(ledger).read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                if r.get("request_sha256") and not r.get("error") and r.get("status") == "completed":
                    self.cache[r["request_sha256"]] = r
        self.model, self.effort, self.max_out = model, effort, max_out
        self.misses, self.hits, self.spent = 0, 0, 0.0

    def __call__(self, system, user):
        body = json.dumps({"model": self.model, "input": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                           "reasoning": {"effort": self.effort}, "max_output_tokens": self.max_out}).encode("utf-8")
        hit = self.cache.get(hashlib.sha256(body).hexdigest())
        if hit is None:
            self.misses += 1
            raise RuntimeError("replay miss (not sent)")
        self.hits += 1
        return LLMResult(hit["output_text"], hit.get("usage") or {}, 0.0, 0.0, hit.get("model", self.model))
