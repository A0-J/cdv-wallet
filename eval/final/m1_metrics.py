"""M1 change-candidate evaluation for the final report (no model calls). Fixed before v4b eval is opened.

Labels: episode_gold.operation_labels (ACCEPT / REJECT / CLARIFY). Predictions of rules v1, rules v2 and M1-G (two runs)
come from eval/v4check/inject_m1g.py rows (same order as episodes.jsonl x candidate_operations); 'UNSUPPORTED' is a
prediction outside the three labels (counted wrong; shown as its own confusion column).
Metadata-only baselines (no dialogue text), trained on dev, evaluated on the target split (dev itself: leave-one-
episode-out), all fixed here without tuning:
  features  cited-turn speaker (role / source), cited turn is the first request, number of candidates in the episode,
            candidate order, dialogue length (turns), cited-turn index, relative position (4 bins), operation, field
  lookup    the four lookup tables of check_dataset.py (majority; operation+field; speaker+first; all four)
  tree      classification tree, Gini, depth 4, at least 5 per leaf, categorical one-vs-rest and numeric thresholds
  nb        categorical naive Bayes, Laplace 1 (numeric features used as categories / bins)
Subsets: all candidates; 'later user turn' = cited turn is a user turn that is not the first request; both also
without the Attribute field (outside the mandate schema).
Per method and subset: accuracy, per-class Precision / Recall / F1, macro-F1, confusion matrix.
Usage: dev  .venv/Scripts/python.exe eval/final/m1_metrics.py --data <v4 or v4b> --split dev --rows <inject rows_dev.jsonl>
       eval .venv/Scripts/python.exe eval/final/m1_metrics.py --data <v4b> --split eval --rows <inject eval rows> (after approval)
Output: --out folder: M1_METRICS_<split>.md, m1_metrics_<split>.json
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

LABELS = ("ACCEPT", "REJECT", "CLARIFY")
CAT = ("role", "first", "op", "field", "n_cand", "order", "relpos")
NUM = ("n_cand", "order", "length", "idx", "relpos_x")


def jl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def items(data: Path, split: str) -> list:
    gold = {g["episode_id"]: g for g in jl(data / split / "episode_gold.jsonl")}
    out = []
    for e in jl(data / split / "episodes.jsonl"):
        turns = {t["turn_id"]: (i, t) for i, t in enumerate(e["dialogue"])}
        first_user = next((t["turn_id"] for t in e["dialogue"] if t["role"] == "user"), None)
        ops = e["candidate_operations"]
        for k, o in enumerate(ops):
            i, t = turns[o["evidence_turn_id"]]
            rel = i / max(1, len(e["dialogue"]) - 1)
            out.append({"episode_id": e["episode_id"], "label": gold[e["episode_id"]]["operation_labels"][o["op_id"]].upper(),
                        "role": t.get("source") or t["role"], "first": t["turn_id"] == first_user, "op": o["operation"],
                        "field": o["field"], "n_cand": min(len(ops), 6), "order": min(k, 5), "length": len(e["dialogue"]),
                        "idx": i, "relpos": min(3, int(rel * 4)), "relpos_x": rel,
                        "later_user": t["role"] == "user" and t["turn_id"] != first_user})
    return out


# ---------------- models
def lookup(train, key):
    tab = defaultdict(Counter)
    for r in train:
        tab[key(r)][r["label"]] += 1
    maj = Counter(r["label"] for r in train).most_common(1)[0][0]
    return lambda r: tab[key(r)].most_common(1)[0][0] if key(r) in tab else maj


LOOKUPS = {"lookup: majority": lambda r: (), "lookup: operation+field": lambda r: (r["op"], r["field"]),
           "lookup: speaker+first": lambda r: (r["role"], r["first"]),
           "lookup: operation+field+speaker+first": lambda r: (r["op"], r["field"], r["role"], r["first"])}


def gini(c: Counter) -> float:
    n = sum(c.values())
    return 1 - sum((v / n) ** 2 for v in c.values()) if n else 0.0


def tree_fit(rows, depth=4, min_leaf=5):
    c = Counter(r["label"] for r in rows)
    node = {"pred": sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]}
    if depth == 0 or len(c) == 1 or len(rows) < 2 * min_leaf:
        return node
    best, base = None, gini(c) * len(rows)
    cands = [("cat", f, v) for f in ("role", "first", "op", "field") for v in sorted({str(r[f]) for r in rows})]
    cands += [("num", f, th) for f in NUM for th in sorted({r[f] for r in rows})[:-1]]
    for kind, f, v in cands:
        left = [r for r in rows if (str(r[f]) == v if kind == "cat" else r[f] <= v)]
        if len(left) < min_leaf or len(rows) - len(left) < min_leaf:
            continue
        right = [r for r in rows if not (str(r[f]) == v if kind == "cat" else r[f] <= v)]
        score = gini(Counter(r["label"] for r in left)) * len(left) + gini(Counter(r["label"] for r in right)) * len(right)
        if score < base - 1e-12 and (best is None or score < best[0] - 1e-12):
            best = (score, kind, f, v, left, right)
    if best is None:
        return node
    _, kind, f, v, left, right = best
    node.update(kind=kind, f=f, v=v, left=tree_fit(left, depth - 1, min_leaf), right=tree_fit(right, depth - 1, min_leaf))
    return node


def tree_predict(node, r):
    while "f" in node:
        go = str(r[node["f"]]) == node["v"] if node["kind"] == "cat" else r[node["f"]] <= node["v"]
        node = node["left"] if go else node["right"]
    return node["pred"]


def nb_fit(rows):
    prior = Counter(r["label"] for r in rows)
    cond = {f: defaultdict(Counter) for f in CAT}
    vals = {f: {str(r[f]) for r in rows} for f in CAT}
    for r in rows:
        for f in CAT:
            cond[f][r["label"]][str(r[f])] += 1

    def pred(r):
        best = None
        for lab in sorted(prior):
            s = math.log(prior[lab] / len(rows))
            for f in CAT:
                s += math.log((cond[f][lab][str(r[f])] + 1) / (prior[lab] + len(vals[f]) + 1))
            if best is None or s > best[0]:
                best = (s, lab)
        return best[1]
    return pred


def fit_predict(train, test, method):
    if method in LOOKUPS:
        f = lookup(train, LOOKUPS[method])
        return [f(r) for r in test]
    if method == "tree (depth 4)":
        t = tree_fit(train)
        return [tree_predict(t, r) for r in test]
    f = nb_fit(train)
    return [f(r) for r in test]


def metrics(gold, pred):
    cm = defaultdict(Counter)
    for g, p in zip(gold, pred):
        cm[g][p] += 1
    out = {"n": len(gold), "accuracy": round(100 * sum(g == p for g, p in zip(gold, pred)) / max(1, len(gold)), 1), "per_class": {}}
    f1s = []
    for lab in LABELS:
        tp = cm[lab][lab]
        fp = sum(cm[g][lab] for g in LABELS if g != lab)
        fn = sum(v for p, v in cm[lab].items() if p != lab)
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
        f1s.append(f1)
        out["per_class"][lab] = {"precision": round(100 * pr, 1), "recall": round(100 * rc, 1), "f1": round(100 * f1, 1), "support": tp + fn}
    out["macro_f1"] = round(100 * sum(f1s) / 3, 1)
    out["confusion"] = {g: dict(cm[g]) for g in LABELS}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--train-data", type=Path, default=None, help="dev source for the baselines (default: --data)")
    ap.add_argument("--rows", type=Path, required=True, help="inject_m1g rows for this split")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    test = items(a.data, a.split)
    rows = jl(a.rows)
    assert len(rows) == len(test), f"inject rows {len(rows)} != candidates {len(test)}"
    for t, r in zip(test, rows):
        assert t["label"] == r["label"] and t["episode_id"] == r["episode_id"], "row order differs from episodes x candidates"
        for k in ("v1", "v2", "m1g_run1", "m1g_run2"):
            t[k] = r[k]
    preds = {"rules v1": [t["v1"] for t in test], "rules v2": [t["v2"] for t in test],
             "M1-G run 1": [t["m1g_run1"] for t in test], "M1-G run 2": [t["m1g_run2"] for t in test]}
    methods = list(LOOKUPS) + ["tree (depth 4)", "naive Bayes"]
    if a.split == "dev":                                         # leave-one-episode-out inside dev
        by = defaultdict(list)
        for i, t in enumerate(test):
            by[t["episode_id"]].append(i)
        for m in methods:
            p = [None] * len(test)
            for e, idx in by.items():
                train = [t for t in test if t["episode_id"] != e]
                for i, y in zip(idx, fit_predict(train, [test[i] for i in idx], m)):
                    p[i] = y
            preds["meta " + m + " (LOEO)"] = p
    else:
        train = items(a.train_data or a.data, "dev")
        for m in methods:
            preds["meta " + m] = fit_predict(train, test, m)
    subsets = {"all": lambda t: True, "later user turn": lambda t: t["later_user"],
               "all, no Attribute": lambda t: t["field"] != "Attribute",
               "later user turn, no Attribute": lambda t: t["later_user"] and t["field"] != "Attribute"}
    res = {}
    md = [f"# M1 변경 후보 평가 ({a.split}, 모델 호출 0; 메타데이터 기준선은 dev 학습" + (", dev 안에서는 여정 하나씩 빼고 학습" if a.split == "dev" else "") + ")", ""]
    for sname, sel in subsets.items():
        idx = [i for i, t in enumerate(test) if sel(t)]
        gold = [test[i]["label"] for i in idx]
        md += [f"## {sname} (n={len(idx)}; 정답 " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(gold).items())) + ")", "",
               "| 방법 | 정확도 | 매크로 F1 | ACCEPT P/R/F1 | REJECT P/R/F1 | CLARIFY P/R/F1 |", "|---|---:|---:|---|---|---|"]
        res[sname] = {}
        for name, p in preds.items():
            m = metrics(gold, [p[i] for i in idx])
            res[sname][name] = m
            pc = m["per_class"]
            md.append(f"| {name} | {m['accuracy']} | {m['macro_f1']} | " + " | ".join(
                f"{pc[l]['precision']}/{pc[l]['recall']}/{pc[l]['f1']}" for l in LABELS) + " |")
        md += ["", "혼동행렬 (행 = 정답, 열 = 예측; ACCEPT / REJECT / CLARIFY / 그 밖)", ""]
        for name in ("rules v1", "rules v2", "M1-G run 1", "M1-G run 2"):
            cm = res[sname][name]["confusion"]
            md.append(f"- {name}: " + "; ".join(f"{g} → " + "/".join(str(cm[g].get(p, 0)) for p in LABELS)
                                                + f"/{sum(v for p, v in cm[g].items() if p not in LABELS)}" for g in LABELS))
        md.append("")
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"m1_metrics_{a.split}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (a.out / f"M1_METRICS_{a.split}.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md[:30]))


if __name__ == "__main__":
    main()
