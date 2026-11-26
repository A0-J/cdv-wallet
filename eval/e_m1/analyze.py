"""E-M1 analysis: paper tables, figures, representative cases. No model calls; reads result rows only.

Every table is labelled with its evidence kind:
  [실제 데이터 · 실제 모델 출력]   R1, R3, R2 (CartTrace test_cross_store / all splits for R2)
  [생성 데이터 · 실제 모델 출력]   G1 templates (extractor = real gpt-6-luna; dialogues generated)
  [실제 데이터 · 모델 호출 없음]   X1 WhisperBench (A-VIP / Standing comparison)
  [정답 mandate 기반 상한]        U (gold ledger, same cart check) and G3
Usage: .venv/Scripts/python.exe eval/e_m1/analyze.py [--rows-suffix ""] [--out results/e_m1_20261126/analysis]
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results" / "e_m1_20261126"
DATA = Path(r"C:/ct/kit/dataset/data")
ARMS = ["plain", "fnctod", "fnctod_r", "fnctod_rn"]
ARM_LABEL = {"plain": "일반 LLM", "fnctod": "FnCTOD", "fnctod_r": "FnCTOD+규칙", "fnctod_rn": "FnCTOD+규칙+NLI"}
LEGIT, VIOL = {"RIGHT", "RIGHT_BY_LUCK"}, {"WRONG", "WRONG_HIDDEN"}
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, MUTED, GRID, SURF = "#0b0b0b", "#5f5e5a", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.family": ["Malgun Gothic", "DejaVu Sans"], "axes.unicode_minus": False,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": MUTED, "font.size": 10})

G1_CAT = {"정당한 변경": ["C1_relax_explicit", "C5_tighten", "C7_explicit_drop_bundle", "C8_add_substitute", "X2_budget_overridden"],
          "부당한 변경": ["C2_relax_no_cue", "C3_relax_seller_source", "C4_relax_value_mismatch", "C9_substitute_no_cue"],
          "의도 불명확": ["C6_ambiguous_pick_bundle", "X1_two_budgets_unresolved", "X3_brand_in_out"],
          "추출 누락": ["O1_omitted_budget"]}


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * max(0, c - h), 100 * min(1, c + h))


def pct(k, n):
    if not n:
        return "–"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.1f}% ({k}/{n}) [{lo:.1f}, {hi:.1f}]"


def load_rows(name):
    p = RES / f"rows_{name}.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l] if p.exists() else None


# ------------------------------------------------------------------ real data metrics (counts)

def real_counts(rows, arm):
    A = [r["arms"][arm] for r in rows]
    legit = [r for r in rows if r["outcome"] in LEGIT]
    viol = [r for r in rows if r["outcome"] in VIOL]
    return {
        "unjust": (sum(a["proposed_wrong"] - a["accepted_wrong"] for a in A), sum(a["proposed_wrong"] for a in A)),
        "legit_acc": (sum(a["accepted_correct"] for a in A), sum(a["proposed_correct"] for a in A)),
        "silent_omit": (sum(a["missing_silent"] for a in A), sum(a["stated_n"] for a in A)),
        "omit_any": (sum(a["missing_stated"] for a in A), sum(a["stated_n"] for a in A)),
        "clarify": (sum(a["hint"] == "CLARIFY" for a in A), len(A)),
        "clarify_legit": (sum(r["arms"][arm]["hint"] == "CLARIFY" for r in legit), len(legit)),
        "legit_blocked": (sum(r["arms"][arm]["decision"] != "ALLOW" for r in legit), len(legit)),
        "viol_allowed": (sum(r["arms"][arm]["decision"] == "ALLOW" for r in viol), len(viol)),
        "verify_ms": sorted(a["verify_ms"] for a in A)[len(A) // 2] if A else None,
    }


def upper_counts(rows):
    legit = [r for r in rows if r["outcome"] in LEGIT]
    viol = [r for r in rows if r["outcome"] in VIOL]
    return {"legit_blocked": (sum(r["upper_bound_decision"] != "ALLOW" for r in legit), len(legit)),
            "viol_allowed": (sum(r["upper_bound_decision"] == "ALLOW" for r in viol), len(viol))}


def real_table(sets):
    L = []
    for name, (title, rows) in sets.items():
        L += [f"### {title} — [실제 데이터 · 실제 모델 출력], 여정 {len(rows)}", "",
              "| 지표 | " + " | ".join(ARM_LABEL[a] for a in ARMS) + " |", "|---|" + "---|" * len(ARMS)]
        cs = {a: real_counts(rows, a) for a in ARMS}
        for key, lab in [("unjust", "부당 조건 탐지율(장부에 안 넣음) ↑"), ("legit_acc", "정상 조건 허용률 ↑"),
                         ("silent_omit", "조용한 조건 누락률(경보 없음) ↓"), ("omit_any", "조건 누락률(경보 포함) ↓"),
                         ("clarify", "사용자 확인 요청률(전체 여정)"), ("clarify_legit", "불필요한 확인 요청률(정상 여정) ↓"),
                         ("legit_blocked", "정상 거래 오차단율 ↓"), ("viol_allowed", "위반 거래 통과율 ↓")]:
            L.append(f"| {lab} | " + " | ".join(pct(*cs[a][key]) for a in ARMS) + " |")
        L.append("| 검증 지연 중앙값(ms) | " + " | ".join(f"{cs[a]['verify_ms']:.1f}" for a in ARMS) + " |")
        ex = sorted(r["extract_s"] for r in rows)
        u = upper_counts(rows)
        L += ["", f"- 추출(API) 지연 중앙값: {ex[len(ex) // 2]:.1f} s/여정 (FnCTOD, 병렬 실행 중 측정). 비용 합계 ${sum(r['cost_usd'] for r in rows):.4f}",
              f"- [정답 mandate 기반 상한] 정답 장부로 같은 결제 검사: 정상 거래 오차단 {pct(*u['legit_blocked'])}, 위반 거래 통과 {pct(*u['viol_allowed'])}",
              "- 일반 LLM·FnCTOD는 검증이 없으므로 부당 조건 탐지율이 정의상 0이고 확인 요청을 하지 않는다.",
              "- 대괄호 = Wilson 95% 구간. 조건 단위 지표는 같은 여정의 조건끼리 독립이 아니라서 구간이 좁게 나올 수 있다.", ""]
    return L


def causes(r, arm):
    a = r["arms"][arm]
    if a["decision"] == "ALLOW":
        return {"ALLOW"}
    why = set()
    if a["decision"] == "DENY" or (a["codes"] and a["hint"] != "CLARIFY"):
        why |= {"DENY:" + x for x in a["codes"]}
    if a["hint"] == "CLARIFY":
        why |= {"경보:" + f.split(":")[0] for f in a["flags"]}
        last = {}
        for t in (r.get("traces") or {}).get(arm) or []:
            for o in t["ops"]:
                last[o[1]] = o
        pend = [k for k, o in last.items() if o[3] == "PENDING"]
        why |= {"확인대기:" + k for k in pend}
        if not a["flags"] and not pend:
            why.add("확인:기타")
    return why


def selectivity_and_causes(sets):
    L = ["### 선별성: 정상 여정과 위반 여정을 막은 비율 비교 (사후 분석, 같은 행 파일)", "",
         "| 세트 | 비교군 | 위반 여정 차단(확인 포함) | 정상 여정 차단(확인 포함) | 차이(%p) |", "|---|---|---|---|---:|"]
    for name, (title, rows) in sets.items():
        legit = [r for r in rows if r["outcome"] in LEGIT]
        viol = [r for r in rows if r["outcome"] in VIOL]
        for a in ARMS + ["U"]:
            dec = (lambda r: r["upper_bound_decision"]) if a == "U" else (lambda r, a=a: r["arms"][a]["decision"])
            kv, kl = sum(dec(r) != "ALLOW" for r in viol), sum(dec(r) != "ALLOW" for r in legit)
            lab = "상한 U(정답 장부)" if a == "U" else ARM_LABEL[a]
            L.append(f"| {name.split('_')[0]} | {lab} | {pct(kv, len(viol))} | {pct(kl, len(legit))} | "
                     f"{(100 * kv / len(viol) if viol else 0) - (100 * kl / len(legit) if legit else 0):+.1f} |")
    L += ["", "- 차이가 0에 가까우면 차단이 위반 여부와 무관하게 일어난다는 뜻이다.", "",
          "### 차단·확인 요청 원인 (정상 여정, 원인이 여럿이면 각각 셈)", "",
          "| 세트 | 비교군 | 정상 여정 수 | 원인 상위 |", "|---|---|---:|---|"]
    from collections import Counter
    for name, (title, rows) in sets.items():
        legit = [r for r in rows if r["outcome"] in LEGIT]
        for a in ("fnctod", "fnctod_r", "fnctod_rn"):
            c = Counter(w for r in legit for w in causes(r, a) if w != "ALLOW")
            L.append(f"| {name.split('_')[0]} | {ARM_LABEL[a]} | {len(legit)} | " + ", ".join(f"{k} {v}" for k, v in c.most_common(6)) + " |")
    L += ["", "- `확인대기:ptype` = FnCTOD가 턴마다 바꾸는 품목 종류(product_type, 채점·결제 검사에 쓰지 않는 약한 항목)의 변경을 "
          "M1이 명시적 근거 없는 변경으로 보고 사용자 확인으로 보낸 경우.",
          "- `확인대기:sub` = 조건부 대체 허용의 범위 확인 대기, `확인대기:qty` = 수량 값이 발화에 그대로 없어 확인 대기(주로 NLI 팔).",
          "- 이 원인 분해는 test 결과를 본 사후 분석이다. 규칙은 바꾸지 않았다.", ""]
    return L


# ------------------------------------------------------------------ G1

def g1_table(rows):
    by = {}
    for cat, tids in G1_CAT.items():
        sub = [r for r in rows if r["template_id"] in tids]
        by[cat] = {a: (sum(r["arms"][a]["correct"] for r in sub), len(sub),
                       sum(r["arms"][a]["hint"] == "CLARIFY" for r in sub)) for a in ARMS}
    L = [f"### G1 템플릿 — [생성 데이터 · 실제 모델 출력], 사례 {len(rows)}", "",
         "| 범주 (정답 동작) | " + " | ".join(ARM_LABEL[a] for a in ARMS) + " |", "|---|" + "---|" * len(ARMS)]
    expl = {"정당한 변경": "정당한 변경 (반영)", "부당한 변경": "부당한 변경 (반영 안 함)",
            "의도 불명확": "의도 불명확 (유지 또는 확인)", "추출 누락": "추출 누락 (경보)"}
    for cat in G1_CAT:
        L.append(f"| {expl[cat]} 정답률 | " + " | ".join(pct(*by[cat][a][:2]) for a in ARMS) + " |")
    k, n = (sum(by["정당한 변경"][a][1] - by["정당한 변경"][a][0] for a in ["fnctod_r"]), by["정당한 변경"]["fnctod_r"][1])
    L += ["", "| 범주별 확인 요청률 | " + " | ".join(ARM_LABEL[a] for a in ARMS) + " |", "|---|" + "---|" * len(ARMS)]
    for cat in G1_CAT:
        L.append(f"| {cat} | " + " | ".join(pct(by[cat][a][2], by[cat][a][1]) for a in ARMS) + " |")
    L += ["", "- 정당한 변경의 오차단율 = 100% − '정당한 변경' 정답률 (반영되지 않거나 확인 대기로 남은 비율).",
          "- 템플릿별 값: `summary_G1_eval.json`의 by_template.", ""]
    per = {}
    for r in rows:
        for a in ARMS:
            d = per.setdefault(r["template_id"], {}).setdefault(a, [0, 0])
            d[0] += r["arms"][a]["correct"]
            d[1] += 1
    L += ["| 템플릿 | " + " | ".join(ARM_LABEL[a] for a in ARMS) + " |", "|---|" + "---|" * len(ARMS)]
    for cat, tids in G1_CAT.items():
        for t in tids:
            if t in per:
                L.append(f"| {cat}: {t} | " + " | ".join(f"{per[t][a][0]}/{per[t][a][1]}" for a in ARMS) + " |")
    return L, by


# ------------------------------------------------------------------ X1 (A-VIP / Standing)

def x1_table():
    p = ROOT / "results/whisperbench_e2_20261126/summary_dev.json"
    if not p.exists():
        return []
    t = json.loads(p.read_text(encoding="utf-8"))["tables"]
    def agg(keys, arm, what):
        return sum(t[k][arm][what] for k in keys), sum(t[k]["n"] for k in keys)
    att = ["main|claim|alt|stock", "cross_seller:S|claim|alt|stock"]
    ben = ["main|noclaim|alt|all", "cross_seller|noclaim|alt|all"]
    rows = [("A-VIP binding", "원본 코드(A0-J/avip_defense, 서브모듈 고정 0c1b538)", "W1",
             "결정된 결제 내용과 서명된 의도의 결합만 검사. 판매자 주장 내용은 보지 않음"),
            ("Standing 규칙", "재구현(논문 규칙; A0-J/standing-not-truth 9f041c0 참고)", "W1",
             "화자 ≠ 대상 판매자일 때만 차단. 이 묶음은 한 판매자가 두 상품을 팔아 화자 = 대상이므로 정의상 A-VIP와 같음"),
            ("A-VIP + 지출 규칙", "재구현", "W2s", "더 비싼 대안을 고르면 재확인"),
            ("A-VIP + E2(제안)", "본 연구 구현", "W2e", "재고 술어의 권한 = 플랫폼. 판매자 문장의 재고 주장은 증거로 인정 안 함")]
    L = ["### A-VIP · Standing 비교 (X1) — [실제 데이터 · 모델 호출 없음], WhisperBench 원본 실행 기록", "",
         "| 비교군 | 구현 | 재고 주장 공격 통과율 ↓ | 정상 선택 재확인율 ↓ | 적용 가정 |", "|---|---|---|---|---|"]
    for name, impl, arm, assume in rows:
        L.append(f"| {name} | {impl} | {pct(*agg(att, arm, 'ALLOW'))} | {pct(*agg(ben, arm, 'CLARIFY'))} | {assume} |")
    L += ["", "- 표본: main + cross_seller 같은 판매자 설정의 재고·단종 주장(alt 서명) 87건, 주장 없는 정상 선택 216건. 개발 분할.",
          "- E2 결과는 '같은 판매자의 문장형 재고 주장'에 한정된다. 전체 공격 방어 성능으로 일반화하지 않는다.", ""]
    return L


# ------------------------------------------------------------------ figures

def fig_real(sets, out):
    keys = [("legit_blocked", "정상 거래 오차단율 ↓"), ("clarify_legit", "불필요한 확인 요청률 ↓"),
            ("silent_omit", "조용한 조건 누락률 ↓"), ("unjust", "부당 조건 탐지율 ↑")]
    for name, (title, rows) in sets.items():
        fig, axs = plt.subplots(1, 4, figsize=(13, 4.0))
        for ax, (key, lab) in zip(axs, keys):
            ks = [real_counts(rows, a)[key] for a in ARMS]
            vals = [100 * k / n if n else 0 for k, n in ks]
            ax.bar(range(4), vals, color=C, width=0.66, edgecolor=SURF, linewidth=2, zorder=3)
            for x, (k, n), v in zip(range(4), ks, vals):
                lo, hi = wilson(k, n)
                if n:
                    ax.errorbar([x], [v], yerr=[[max(0, v - lo)], [max(0, hi - v)]], fmt="none", ecolor=MUTED, capsize=3, zorder=4)
                    ax.text(x, min(max(v, hi), 100) + 3, f"{v:.0f}%\n({k}/{n})", ha="center", va="bottom", fontsize=8, color=INK)
            ax.set_xticks(range(4), [ARM_LABEL[a].replace("+", "\n+") for a in ARMS], fontsize=7.5)
            ax.set_ylim(0, 125)
            ax.set_yticks([0, 25, 50, 75, 100])
            ax.yaxis.grid(True, color=GRID, zorder=0)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
            ax.set_title(lab, fontsize=10, loc="left")
        fig.suptitle(f"E-M1 {title} — 실제 CartTrace 대화, 실제 gpt-6-luna 추출 (FnCTOD 세 팔은 같은 추출 결과)", fontsize=10.5, x=0.01, ha="left")
        fig.text(0.01, 0.01, "막대 위 = 비율(건수), 오차 막대 = Wilson 95%. 부당 조건 탐지율은 검증이 없는 일반 LLM·FnCTOD에서 정의상 0.", fontsize=8, color=MUTED)
        fig.tight_layout(rect=(0, 0.04, 1, 0.93))
        fig.savefig(out / f"fig_e_m1_{name}.png", dpi=200)
        plt.close(fig)


def fig_g1(by, out):
    cats = list(G1_CAT)
    fig, ax = plt.subplots(figsize=(11, 4.4))
    w = 0.2
    for i, a in enumerate(ARMS):
        vals = [100 * by[c][a][0] / by[c][a][1] if by[c][a][1] else 0 for c in cats]
        xs = [j + (i - 1.5) * w for j in range(len(cats))]
        ax.bar(xs, vals, width=w, color=C[i], edgecolor=SURF, linewidth=2, label=ARM_LABEL[a], zorder=3)
        for x, v in zip(xs, vals):
            ax.text(x, v + 2, f"{v:.0f}", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(range(len(cats)), ["정당한 변경\n(반영해야 함)", "부당한 변경\n(반영하면 안 됨)", "의도 불명확\n(유지 또는 확인)", "추출 누락\n(경보)"])
    ax.set_ylim(0, 115)
    ax.set_ylabel("정답률 (%)")
    ax.yaxis.grid(True, color=GRID, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.2), fontsize=8.5)
    ax.set_title("E-M1 G1 — 생성 대화(템플릿 13종 × 20), 실제 gpt-6-luna 추출", fontsize=10.5, loc="left")
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.3)
    fig.savefig(out / "fig_e_m1_G1_by_category.png", dpi=200)
    plt.close(fig)


# ------------------------------------------------------------------ cases

def user_turns(eids, splits=("test_cross_store", "validation", "train", "test_cross_template")):
    got = {}
    for s in splits:
        for f in glob.glob(str(DATA / "turns" / f"{s}-*.parquet")):
            for x in pq.read_table(f, columns=["episode_id", "seq", "actor", "kind", "text"],
                                   filters=[("actor", "=", "shopper")]).to_pylist():
                if x["episode_id"] in eids and x["kind"] == "message" and (x["text"] or "").strip():
                    got.setdefault(x["episode_id"], []).append((x["seq"], x["text"]))
    return {e: sorted(v) for e, v in got.items()}


def pick_cases(sets):
    picks = []
    for name, (title, rows) in sets.items():
        def first(pred, label, k=1):
            for r in rows:
                if pred(r):
                    picks.append((label, title, r))
                    k -= 1
                    if k == 0:
                        return
        first(lambda r: r["outcome"] in VIOL and r["arms"]["fnctod"]["decision"] == "ALLOW"
              and r["arms"]["fnctod_r"]["decision"] != "ALLOW", "성공: 검증 없는 FnCTOD는 통과시킨 위반 거래를 M1이 막음")
        first(lambda r: r["outcome"] in LEGIT and r["arms"]["fnctod_r"]["decision"] == "ALLOW"
              and r["arms"]["fnctod"]["proposed_wrong"] > 0 and r["arms"]["fnctod_r"]["accepted_wrong"] == 0,
              "성공: 근거 없는 조건을 장부에서 빼고 정상 거래는 통과")
        first(lambda r: r["outcome"] in LEGIT and r["arms"]["fnctod_r"]["decision"] != "ALLOW", "실패: 정상 거래를 막거나 확인 요청(오차단)")
        first(lambda r: r["outcome"] in VIOL and all(r["arms"][a]["decision"] == "ALLOW" for a in ARMS),
              "실패: 모든 팔과 상한(정답 장부)도 통과시킨 위반 거래")
    return picks


def cases_md(sets):
    picks = pick_cases(sets)
    ut = user_turns({r["episode_id"] for _, _, r in picks})
    L = ["# E-M1 대표 사례 (자동 선정, 규칙: 각 세트에서 조건을 만족하는 첫 여정)", "",
         "> [실제 데이터 · 실제 모델 출력]. CartTrace 발화는 CC BY 4.0(generalmachines/CartTrace-100k), 짧게 발췌.", ""]
    for label, title, r in picks:
        L += [f"## {label} — {title} `{r['episode_id']}` (결과 {r['outcome']})", "",
              "- 사용자 발화: " + " / ".join(f"`s{s}` {t[:140]}" for s, t in ut.get(r["episode_id"], [])[:6]),
              f"- 정답 사양(채점용): {r['gold']}",
              f"- FnCTOD 최종 상태: {json.dumps(r['fnctod_states'][-1]['state'] if r['fnctod_states'] else {}, ensure_ascii=False)[:400]}"]
        for a in ARMS:
            x = r["arms"][a]
            L.append(f"- {ARM_LABEL[a]}: 판정 **{x['decision']}** · 장부 {json.dumps(x['ledger'], ensure_ascii=False)[:220]} · 경보 {x['flags']} · 결제 검사 {x['codes']}")
        tr = (r.get("traces") or {}).get("fnctod_r") or []
        ops = [f"`s{t['seq']}` {o[0]} {o[1]} ({o[2]}) → {o[3]} {o[4]}" for t in tr for o in t["ops"] if o[3] != "ACCEPT"]
        if ops:
            L.append("- M1(규칙)이 받아들이지 않은 연산: " + "; ".join(dict.fromkeys(ops)))
        L.append("")
    return L


G1_FILE = Path(r"C:/ct/runs/cdv_wallet/generated/G1/eval.jsonl")


def g1_cases(rows):
    """[생성 데이터 · 실제 모델 출력] cases: first row per rule."""
    src = {json.loads(l)["case_id"]: json.loads(l) for l in G1_FILE.read_text(encoding="utf-8").splitlines() if l}
    rules = [("성공(생성): 모호한 고르기를 묶음 철회로 받아들이지 않음", "C6_ambiguous_pick_bundle",
              lambda r: not r["arms"]["fnctod"]["correct"] and r["arms"]["fnctod_r"]["correct"]),
             ("성공(생성): 브랜드 포함·제외 충돌을 확인 요청", "X3_brand_in_out",
              lambda r: not r["arms"]["fnctod"]["correct"] and r["arms"]["fnctod_r"]["correct"]),
             ("실패(생성): 추출기는 맞았는데 M1이 틀림", None,
              lambda r: r["arms"]["fnctod"]["correct"] and not r["arms"]["fnctod_r"]["correct"]),
             ("실패(생성): 정당한 명시적 묶음 제외를 모든 팔이 반영 못 함", "C7_explicit_drop_bundle",
              lambda r: not any(r["arms"][a]["correct"] for a in ARMS))]
    L = ["# G1 대표 사례 — [생성 데이터 · 실제 모델 출력]", ""]
    for label, tid, pred in rules:
        for r in rows:
            if (tid is None or r["template_id"] == tid) and pred(r):
                c = src.get(r["case_id"], {})
                L += [f"## {label} — `{r['case_id']}`", "",
                      "- 사용자 발화: " + " / ".join(u["text"][:160] for u in c.get("user_turns", [])),
                      "- 외부(판매자) 문장: " + (" / ".join(x["text"][:120] for x in c.get("external_texts") or []) or "없음"),
                      f"- FnCTOD 최종 상태: {json.dumps(r['fnctod_states'][-1]['state'] if r.get('fnctod_states') else {}, ensure_ascii=False)[:300]}"]
                L += [f"- {ARM_LABEL[a]}: {'정답' if r['arms'][a]['correct'] else '오답'} · 힌트 {r['arms'][a]['hint']}" for a in ARMS]
                L.append("")
                break
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RES / "analysis"))
    ap.add_argument("--sets", default="R1_test_cross_store,R3_test_cross_store,R2_test_cross_store")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    titles = {"R1": "R1 실제 일반 여정", "R3": "R3 조건부 대체 + 실제 품절", "R2": "R2 품절 → 고르기 → 거절 (의도 불명확)",
              "R1_validation": "파일럿"}
    sets = {}
    for n in a.sets.split(","):
        rows = load_rows(n)
        if rows:
            sets[n] = (titles.get(n.split("_")[0], n) if "validation" not in n else "파일럿(validation)", rows)
    L = ["# E-M1 결과표 (논문용 초안 표, 숫자는 행 파일에서 다시 계산)", "",
         "증거 종류: [실제 데이터 · 실제 모델 출력] / [생성 데이터 · 실제 모델 출력] / [실제 데이터 · 모델 호출 없음] / [정답 mandate 기반 상한] / [수동 구성 사례]", "",
         "- 의도 불명확 사례(R2: 품절 뒤 고르기, G1의 C6·X1·X3)는 명백한 위반(R1의 WRONG 결과, G1의 C2·C3·C4·C9)과 따로 보고한다.",
         "- [수동 구성 사례]는 `docs/WALKTHROUGH_ep-b63223f61e0a.md`(FnCTOD 출력을 사람이 씀)뿐이며 여기 숫자에 들어가지 않는다.", ""]
    L += real_table(sets)
    L += selectivity_and_causes(sets)
    g1 = load_rows("G1_eval")
    by = None
    if g1:
        gl, by = g1_table(g1)
        L += gl + [""]
    L += x1_table()
    (out / "TABLES.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    fig_real(sets, out)
    if by:
        fig_g1(by, out)
    cl = cases_md(sets) + (g1_cases(g1) if g1 else [])
    (out / "CASES.md").write_text("\n".join(cl) + "\n", encoding="utf-8", newline="\n")
    print("wrote", sorted(p.name for p in out.iterdir()))


if __name__ == "__main__":
    sys.exit(main())
