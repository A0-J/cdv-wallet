"""Runner change (adjustment history: runner, not rules/prompts/policy), researcher decision 2026-11-27:
within ONE run, an M1-G request with the same input (system prompt + user text, i.e. prompt version + user turn +
change description) is sent once and its answer is shared by every transaction and configuration (B3, B4, B3 rows of
matched cases ...). Runs never share answers: each run gets its own empty ledger. Pre-warming sends the distinct
requests of all transactions in parallel before the (unchanged, sequential) decision loop.
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import threading


class MemoLLM:
    def __init__(self, llm):
        self.llm, self.memo, self.lock = llm, {}, threading.Lock()
        self.requested = 0                       # calls the decision code asked for (before reuse)

    def __call__(self, system, user):
        k = hashlib.sha256((system + "\x00" + user).encode("utf-8")).hexdigest()
        with self.lock:
            self.requested += 1
            f = self.memo.get(k)
            owner = f is None
            if owner:
                f = self.memo[k] = cf.Future()
        if owner:
            try:
                f.set_result(self.llm(system, user))
            except BaseException as e:  # noqa: BLE001 - re-raised to every caller, as a direct call would
                f.set_exception(e)
        return f.result()

    @property
    def distinct(self):
        return len(self.memo)

    def __getattr__(self, name):               # spent, cache_hits, ... of the wrapped client
        return getattr(self.llm, name)


def prewarm(jobs, memo: MemoLLM, workers: int = 8):
    """jobs: callables that run the M1-G path for one transaction with `memo` (their results are discarded)."""
    errors = 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for fut in [ex.submit(j) for j in jobs]:
            try:
                fut.result()
            except SystemExit:
                raise
            except Exception:  # noqa: BLE001 - the sequential loop meets the same error again and handles it
                errors += 1
    return errors
