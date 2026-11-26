"""NLI model selection for V-B (grounding) and V-X (contradiction). Local CPU, no paid calls.

Plan: results/nli_selection_20261126/PLAN.md. Run with the cdv-wallet .venv:
  .venv/Scripts/python.exe eval/nli/select_nli.py --split validation|test_cross_store [--models m1,m2]
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(r"C:/ct/kit/dataset/data")
OUTDIR = ROOT / "results" / "nli_selection_20261126"
MODELS = ["cross-encoder/nli-deberta-v3-base", "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"]
SEED = 20261127
PER = 40


def pairs(split: str):
    rows = []
    for f in sorted(glob.glob(str(DATA / "messages" / "*" / f"{split}-*.parquet"))):
        rows += pq.read_table(f, columns=["episode_id", "hidden_spec", "opening", "kind"]).to_pylist()
    rows = [r for r in rows if r["kind"] == "baseline" and r["opening"]]
    rows.sort(key=lambda r: r["episode_id"])
    by = defaultdict(list)
    for r in rows:
        h = json.loads(r["hidden_spec"])
        for p in h.get("predicates") or []:
            if p.get("source") != "stated":
                continue
            v = p.get("value")
            if p["op"] == "max_price" and isinstance(v, dict):
                x = round(v["amount"] / 100)
                by["budget"].append((r["opening"], f"The customer wants to spend at most ${x}.",
                                     f"The customer wants to spend at most ${x * 2}."))
            elif p["op"] == "count":
                try:
                    n = int(v)
                except (TypeError, ValueError):
                    continue
                by["quantity"].append((r["opening"], f"The customer wants {n} items.", f"The customer wants {n + 2} items."))
            elif p["op"] == "prefer":
                by["substitute"].append((r["opening"],
                                         "The customer accepts a similar item if the requested one is out of stock.",
                                         "The customer does not accept any substitute if the requested one is out of stock."))
        f = (h.get("buyer") or {}).get("fulfillment") or {}
        if f.get("source") == "stated":
            pick = f.get("value") == "pickup"
            pos = "The customer will collect the order from the store." if pick else "The customer wants the order shipped."
            neg = "The customer wants the order shipped." if pick else "The customer will collect the order from the store."
            by["fulfillment"].append((r["opening"], pos, neg))
            if f.get("deadline_days"):
                d = int(f["deadline_days"])
                by["deadline"].append((r["opening"], f"The customer needs delivery within {d} days.",
                                       f"The customer needs delivery within {d + 20} days."))
    rng = random.Random(SEED)
    out = {}
    for k, v in sorted(by.items()):
        out[k] = rng.sample(v, min(PER, len(v)))
    return out


def run_model(name, data):
    tok = AutoTokenizer.from_pretrained(name)
    model = AutoModelForSequenceClassification.from_pretrained(name).eval()
    lab = {v.lower(): int(k) for k, v in model.config.id2label.items()}
    ent, con = lab["entailment"], lab["contradiction"]
    res, times = {}, []
    with torch.inference_mode():
        for field, items in data.items():
            c = defaultdict(int)
            for prem, pos, neg in items:
                for kind, hyp in (("pos", pos), ("neg", neg)):
                    t0 = time.perf_counter()
                    x = tok(prem, hyp, return_tensors="pt", truncation=True, max_length=512)
                    pred = int(model(**x).logits.argmax(-1))
                    times.append(time.perf_counter() - t0)
                    c[f"{kind}_n"] += 1
                    c[f"{kind}_entail"] += pred == ent
                    c[f"{kind}_contra"] += pred == con
            res[field] = {"n_pos": c["pos_n"], "grounding_recall_pct": round(100 * c["pos_entail"] / c["pos_n"], 1),
                          "false_grounding_pct": round(100 * c["neg_entail"] / c["neg_n"], 1),
                          "contradiction_on_altered_pct": round(100 * c["neg_contra"] / c["neg_n"], 1)}
    tot = lambda key: sum(r[key] * r["n_pos"] for r in res.values()) / sum(r["n_pos"] for r in res.values())
    return {"by_field": res, "overall": {"grounding_recall_pct": round(tot("grounding_recall_pct"), 1),
                                         "false_grounding_pct": round(tot("false_grounding_pct"), 1),
                                         "contradiction_on_altered_pct": round(tot("contradiction_on_altered_pct"), 1)},
            "latency_ms_median": round(1000 * statistics.median(times), 1), "id2label": model.config.id2label}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["validation", "test_cross_store"], required=True)
    ap.add_argument("--models", default=",".join(MODELS))
    a = ap.parse_args()
    torch.manual_seed(0)
    plan = hashlib.sha256((OUTDIR / "PLAN.md").read_bytes()).hexdigest()
    data = pairs(a.split)
    out = {"plan_sha256": plan, "split": a.split, "post_hoc": a.split == "test_cross_store", "paid_calls": 0,
           "pairs_per_field": {k: len(v) for k, v in data.items()}, "models": {}}
    for m in a.models.split(","):
        out["models"][m] = run_model(m, data)
        print(m, json.dumps(out["models"][m]["overall"]), out["models"][m]["latency_ms_median"], "ms")
    out["plan_sha256_at_end"] = hashlib.sha256((OUTDIR / "PLAN.md").read_bytes()).hexdigest()
    (OUTDIR / f"summary_{a.split}.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
