"""Pre-registered primary comparisons (decision 2026-11-27; results/frozen_610a97c/PREREG_PRIMARY.md). No model calls.

Each endpoint compares two arms on the SAME units (paired):
  x_i, y_i in {0,1}: the endpoint event (ALLOW, or CLARIFY for the re-confirmation endpoint) for arm X and arm Y
  estimate  d = mean(x) - mean(y)  (percentage points)
  95% CI    cluster bootstrap: resample clusters with replacement, 10,000 times, seed 20261127, percentile
  p         paired cluster sign-flip permutation test on per-cluster sums s_c = sum(x_i - y_i), statistic |sum s_c|,
            exact when at most 16 clusters have s_c != 0, otherwise 100,000 random flips (seed 20261127), two-sided
  secondary exact McNemar on units (ignores clustering)
Holm-Bonferroni over the endpoints of one family at family-wise alpha 0.05. Significance is never judged from CI overlap.
A result 'matches' the stated expectation when the Holm-adjusted test is significant in the expected direction; for
'same or more / same or fewer' endpoints it is 'consistent' when there is no Holm-significant difference in the
opposite direction (no equivalence claim: no margin was pre-specified).

Input: a JSONL of units {"unit", "cluster", "<endpoint group flags>", "arms": {arm: decision}} built by the caller.
API: endpoint(units, x, y, event) -> dict ; holm(results) -> results with p_holm
"""
from __future__ import annotations

import itertools
import math
import random

SEED = 20261127


def _event(dec: str, event: str) -> int:
    return int(dec == event)


def mcnemar(x, y) -> float:
    b = sum(1 for p, q in zip(x, y) if p and not q)
    c = sum(1 for p, q in zip(x, y) if q and not p)
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def endpoint(units: list, x: str, y: str, event: str, n_boot: int = 10000, n_perm: int = 100000) -> dict:
    """units: [{"cluster": c, "arms": {x: dec, y: dec}}] (already restricted to the endpoint's population)."""
    xs = [_event(u["arms"][x], event) for u in units]
    ys = [_event(u["arms"][y], event) for u in units]
    n = len(units)
    if n == 0:
        return {"n": 0}
    clusters = {}
    for u, a, b in zip(units, xs, ys):
        c = clusters.setdefault(u["cluster"], [0, 0, 0])
        c[0] += a
        c[1] += b
        c[2] += 1
    keys = sorted(clusters)
    d = 100 * (sum(xs) - sum(ys)) / n
    rng = random.Random(SEED)
    boots = []
    for _ in range(n_boot):
        pick = [clusters[keys[rng.randrange(len(keys))]] for _ in keys]
        m = sum(p[2] for p in pick)
        boots.append(100 * (sum(p[0] for p in pick) - sum(p[1] for p in pick)) / m)
    boots.sort()
    s = [clusters[k][0] - clusters[k][1] for k in keys]
    nz = [v for v in s if v != 0]
    obs = abs(sum(nz))
    if not nz:
        p = 1.0
    elif len(nz) <= 16:
        tot = sum(1 for signs in itertools.product((1, -1), repeat=len(nz)) if abs(sum(v * g for v, g in zip(nz, signs))) >= obs)
        p = tot / 2 ** len(nz)
    else:
        rng2 = random.Random(SEED)
        hit = sum(1 for _ in range(n_perm) if abs(sum(v if rng2.random() < 0.5 else -v for v in nz)) >= obs)
        p = (hit + 1) / (n_perm + 1)
    return {"n": n, "clusters": len(keys), "x": x, "y": y, "event": event, "x_count": sum(xs), "y_count": sum(ys),
            "x_pct": round(100 * sum(xs) / n, 1), "y_pct": round(100 * sum(ys) / n, 1), "diff_pp": round(d, 1),
            "ci95": [round(boots[int(0.025 * n_boot)], 1), round(boots[int(0.975 * n_boot) - 1], 1)],
            "p_perm": round(p, 5), "p_mcnemar_units": round(mcnemar(xs, ys), 5),
            "discordant": {f"{x}_only": sum(1 for a, b in zip(xs, ys) if a and not b),
                           f"{y}_only": sum(1 for a, b in zip(xs, ys) if b and not a)}}


def holm(results: list, alpha: float = 0.05) -> list:
    """results: list of dicts with 'p_perm'; adds 'p_holm' and 'reject' (family-wise alpha)."""
    order = sorted(range(len(results)), key=lambda i: results[i].get("p_perm", 1.0))
    m = len(results)
    running = 0.0
    for rank, i in enumerate(order):
        adj = min(1.0, (m - rank) * results[i].get("p_perm", 1.0))
        running = max(running, adj)
        results[i]["p_holm"] = round(running, 5)
        results[i]["reject"] = running < alpha
    return results


def verdict(r: dict, expect: str) -> str:
    """expect: 'x<y', 'x>y', 'x<=y', 'x>=y' on the endpoint event rate."""
    if r.get("n", 0) == 0:
        return "자료 없음"
    sig = r["reject"]
    sign = (r["diff_pp"] > 0) - (r["diff_pp"] < 0)
    if expect in ("x<y", "x>y"):
        want = -1 if expect == "x<y" else 1
        return "예상과 일치(유의)" if sig and sign == want else ("반대 방향 유의" if sig else "유의한 차이 없음")
    opp = 1 if expect == "x<=y" else -1
    return "반대 방향 유의(예상과 불일치)" if sig and sign == opp else ("예상 방향 유의" if sig else "예상과 모순 없음(동등성 주장 아님)")
