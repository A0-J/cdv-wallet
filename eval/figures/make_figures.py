"""Figures from completed, model-call-free results (no new experiment).

fig1  WhisperBench (original data): same-seller stock/lifecycle claims — attack pass-through and benign
      re-confirmation, per gate. Standing rule (re-implemented): blocks only when speaker != subject seller,
      so on this subset it equals the A-VIP seller rule by definition.
fig2  G3 (generated, gold mandates = upper bound): price-neutral attacks blocked per gate.
fig3  CartTrace (original user turns, gold ledger input = detector-only): omission detection per field.
Palette: reference categorical slots 1-4 (validator not run: node unavailable); every bar carries a value label.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "figures_20261126"
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, MUTED, GRID, SURF = "#0b0b0b", "#5f5e5a", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.family": ["Malgun Gothic", "DejaVu Sans"], "axes.unicode_minus": False,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": MUTED, "font.size": 10})


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * max(0, c - h), 100 * min(1, c + h))


def bars(ax, labels, ks, ns, colors, title):
    xs = range(len(labels))
    vals = [100 * k / n for k, n in zip(ks, ns)]
    err = [[max(0.0, v - wilson(k, n)[0]) for v, k, n in zip(vals, ks, ns)], [max(0.0, wilson(k, n)[1] - v) for v, k, n in zip(vals, ks, ns)]]
    ax.bar(xs, vals, color=colors, width=0.62, edgecolor=SURF, linewidth=2, zorder=3)
    ax.errorbar(xs, vals, yerr=err, fmt="none", ecolor=MUTED, elinewidth=1, capsize=3, zorder=4)
    for x, v, k, n in zip(xs, vals, ks, ns):
        ax.text(x, min(max(v, wilson(k, n)[1]), 100) + 3, f"{v:.0f}%\n({k}/{n})", ha="center", va="bottom", fontsize=9, color=INK)
    ax.set_xticks(list(xs), labels, fontsize=9)
    ax.set_ylim(0, 125)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.yaxis.grid(True, color=GRID, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_title(title, fontsize=10.5, color=INK, loc="left")


def fig1():
    d = json.loads((ROOT / "results/whisperbench_e2_20261126/summary_dev.json").read_text(encoding="utf-8"))["tables"]
    def cell(key, arm, what):
        return d[key][arm][what], d[key]["n"]
    keys_att = ["main|claim|alt|stock", "cross_seller:S|claim|alt|stock"]
    keys_ben = ["main|noclaim|alt|all", "cross_seller|noclaim|alt|all"]
    def agg(keys, arm, what):
        k = sum(cell(x, arm, what)[0] for x in keys)
        n = sum(cell(x, arm, what)[1] for x in keys)
        return k, n
    labels = ["A-VIP binding\n(원본 코드)", "Standing 규칙\n(재구현)", "A-VIP\n+ 지출 규칙", "A-VIP + E2\n(제안)"]
    arms = ["W1", "W1", "W2s", "W2e"]
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.4))
    att = [agg(keys_att, a, "ALLOW") for a in arms]
    bars(axs[0], labels, [k for k, _ in att], [n for _, n in att], C, "① 같은 판매자의 재고·단종 주장 공격 통과율 (낮을수록 좋음)")
    ben = [agg(keys_ben, a, "CLARIFY") for a in arms]
    bars(axs[1], labels, [k for k, _ in ben], [n for _, n in ben], C, "② 주장 없는 정상 선택의 불필요한 재확인율 (낮을수록 좋음)")
    fig.suptitle("WhisperBench 원본 실행 기록 (main + cross_seller 같은 판매자 설정, 모델 호출 0)", fontsize=11, color=INK, x=0.01, ha="left")
    fig.text(0.01, 0.005, "Standing 규칙은 화자≠대상 판매자일 때만 차단하므로 이 묶음(한 판매자가 두 상품 판매)에서는 A-VIP와 같은 값이다. "
             "막대 위 = 비율(건수), 오차 막대 = Wilson 95%.", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(OUT / "fig1_whisperbench_same_seller_stock.png", dpi=200)


def fig2():
    s = json.loads((ROOT / "results/g3_whisperbench_20261126/summary.json").read_text(encoding="utf-8"))["splits"]["eval"]["table"]
    arms = [("W1", "A-VIP binding"), ("W2s", "+ 지출 규칙"), ("W2e", "+ E2"), ("P+E2", "제안 게이트\n(정답 mandate)")]
    rows = [("a|alt|gold=BLOCK", "같은 가격\n브랜드 위반"), ("b|alt|gold=BLOCK", "같은 가격\n가짜 품절"), ("c|alt|gold=BLOCK", "같은 가격\n기준 주입")]
    fig, ax = plt.subplots(figsize=(10.5, 4.4))
    w = 0.2
    for i, (arm, lab) in enumerate(arms):
        vals = [100 * s[r][arm]["correct"] / s[r][arm]["n"] for r, _ in rows]
        xs = [j + (i - 1.5) * w for j in range(len(rows))]
        ax.bar(xs, vals, width=w, color=C[i], edgecolor=SURF, linewidth=2, label=lab, zorder=3)
        for x, v in zip(xs, vals):
            ax.text(x, v + 2, f"{v:.0f}%", ha="center", va="bottom", fontsize=8.5, color=INK)
    ax.set_xticks(range(len(rows)), [l for _, l in rows])
    ax.set_ylim(0, 115)
    ax.yaxis.grid(True, color=GRID, zorder=0)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_ylabel("공격 상품을 막은 비율 (%)")
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.16), fontsize=8.5)
    ax.set_title("G3 생성 데이터 (cross_seller 140쌍): 가격이 오르지 않는 공격 — 정답 mandate를 쓴 상한 결과", fontsize=10.5, loc="left")
    fig.text(0.01, 0.005, "생성 데이터, 정답 mandate 입력(상한·기능 검증). 기준 주입(c)은 M2b 미구현으로 모든 팔 0%.", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.subplots_adjust(bottom=0.3)
    fig.savefig(OUT / "fig2_g3_price_neutral_upper_bound.png", dpi=200)


def fig3(src="summary_test_cross_store.json", name="fig3_omission_detection_realtext.png", note=""):
    d = json.loads((ROOT / "results/omission_realtext_20261126" / src).read_text(encoding="utf-8"))["detection_by_field"]
    order = [("budget_max", "예산"), ("deadline_days", "배송 기한"), ("quantity", "수량"), ("substitute", "조건부 대체"),
             ("fulfillment", "수령 방식"), ("brand_in", "브랜드 포함"), ("brand_out", "브랜드 제외")]
    fig, ax = plt.subplots(figsize=(10.5, 4.2))
    bars(ax, [l for _, l in order], [d[k]["detected"] for k, _ in order], [d[k]["n"] for k, _ in order], [C[0]] * len(order),
         "M1 누락 검사: 조건 하나를 장부에서 뺐을 때 실제 쇼핑객 발화에서 찾아낸 비율")
    fig.text(0.01, 0.005, "CartTrace test_cross_store(사후 표시) 실제 발화, 정답 장부 입력(검사기 단독). 묶음(100%)은 템플릿 첫 발화로 과대평가 가능해 제외." + note,
             fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / name, dpi=200)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    fig1()
    fig2()
    fig3()
    fig3("summary_test_cross_store_v3_rulefix.json", "fig3_omission_detection_realtext_v3_rulefix.png",
         " 규칙 수정판(v3): 매장 수령 표현, '품절이면 알려줘' 오인 수정.")
    print("saved", sorted(p.name for p in OUT.glob("*.png")))
