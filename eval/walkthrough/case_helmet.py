"""Walkthrough on one real CartTrace dialogue (ep-b63223f61e0a, validation, outcome WRONG).

The FnCTOD outputs below are HAND-WRITTEN for illustration (not model outputs): they show the failure
the experiment measures (the extractor turns an ambiguous pick into dropping a required bundle item).
After the paid run is approved, rerun with --live to replace them with real gpt-6-luna outputs.
CartTrace text: CC BY 4.0 (generalmachines/CartTrace-100k), short excerpts.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cdv.canon import canonical_json, new_signing_key, public_of, sha256_hex, sign, verify  # noqa: E402
from cdv.extract import FnCTOD, ScriptedLLM, Turn  # noqa: E402
from cdv.m1 import Ledger, UserTurn  # noqa: E402
from cdv.nli import NLI  # noqa: E402
from cdv.pipeline import cart_check, run_verified, state_to_entries  # noqa: E402

EP, SPLIT = "ep-b63223f61e0a", "validation"
D = Path(r"C:/ct/kit/dataset/data")

PC = "set_purchase_conditions"
SCRIPT = [  # per user turn: (selection, arguments) -- illustrative
    ("<domain>set_purchase_conditions</domain>",
     '<function_call> {"function": "set_purchase_conditions", "arguments": {"required_items": ["Tire Pressure Sensor", '
     '"RXR FULL FACE HELMET"], "quantity": 2, "fulfillment": "pickup"}} </function_call>'),
    ("<domain>none</domain>", None),                       # "I'll go with Tire Pressure Sensor."
    ("<domain>none</domain>", None),                       # "I'll go with muted black."
    ("<domain>none</domain>", None),                       # "Yes, place the order for $112.30."
    ("<domain>none</domain>", None),                       # "No preference on the color..."
    ("<domain>set_purchase_conditions</domain>",            # "I'll go with Helmet."  -> extractor drops the sensor
     '<function_call> {"function": "set_purchase_conditions", "arguments": {"required_items": ["RXR FULL FACE HELMET"], '
     '"quantity": 1, "fulfillment": "pickup"}} </function_call>'),
    ("<domain>none</domain>", None),                       # "That isn't what I asked for..."
]


def main():
    t = pq.read_table(glob.glob(str(D / "turns" / f"{SPLIT}-*.parquet"))[0],
                      columns=["episode_id", "seq", "actor", "kind", "text"],
                      filters=[("episode_id", "=", EP)]).to_pylist()
    msgs = [x for x in sorted(t, key=lambda z: z["seq"]) if x["kind"] == "message" and x["actor"] in ("shopper", "agent")
            and (x["text"] or "").strip()]
    row = None
    for f in glob.glob(str(D / "messages" / "*" / f"{SPLIT}-*.parquet")):
        for r in pq.read_table(f, columns=["episode_id", "hidden_spec", "final_cart", "outcome_class"],
                               filters=[("episode_id", "=", EP)]).to_pylist():
            row = r
    dialogue = [Turn("user" if x["actor"] == "shopper" else "assistant", x["text"], f"s{x['seq']}") for x in msgs]
    users = [UserTurn(f"s{x['seq']}", x["seq"], x["text"]) for x in msgs if x["actor"] == "shopper"]
    replies = []
    for sel, args in SCRIPT:
        replies.append(sel)
        if args:
            replies.append(args)
    fn = FnCTOD(ScriptedLLM(replies)).run(dialogue)
    for st in fn:
        st["seq"] = int(st["turn_id"][1:])
    cart = [{"title": l["title"], "unit_price": l["unit_price"] / 100, "quantity": l["quantity"]}
            for l in json.loads(row["final_cart"])["lines"]]
    lines = [f"# 전체 동작 예시: {EP} (CartTrace {SPLIT}, 결과 {row['outcome_class']})", "",
             "> **주의:** 2단계의 FnCTOD 출력은 설명용으로 사람이 쓴 값이다(모델 출력 아님). 유료 실행 승인 뒤 실제 출력으로 바꾼다.",
             "> CartTrace 발화는 CC BY 4.0(generalmachines/CartTrace-100k)이며 짧게 발췌했다.", "",
             "## 1. 원본 (사용자 발화만, 순서대로)"]
    lines += [f"- `{u.turn_id}` {u.text[:150]}" for u in users]
    lines += ["", "- 숨은 사양(채점에만 씀): " + "; ".join(p["say"] for p in json.loads(row["hidden_spec"])["predicates"]),
              f"- 기록된 최종 장바구니: {[(c['title'][:45], c['unit_price'], c['quantity']) for c in cart]}", "",
              "## 2. FnCTOD 추출 (사용자 턴마다 2단계: 함수 선택 → 인자 생성)"]
    for st in fn:
        lines.append(f"- `s{st['seq']}` 선택 {st['selected'] or ['none']} → 상태 {json.dumps(st['state'].get(PC, {}), ensure_ascii=False)}")
    plain_led = Ledger(1, tuple(state_to_entries(fn[-1]["state"]).values()))
    res = run_verified(fn, users)
    lines += ["", "## 3. M1 검증 (fnctod_r: 규칙. FnCTOD는 인용을 내지 않으므로 M1이 사용자 발화 전체에서 근거를 찾는다)"]
    seen = {}
    for tr in res["trace"]:
        for op in tr["ops"]:
            key = (op[0], op[1], op[3], tuple(op[4]))
            if seen.get(op[1]) == key:     # same rejected op re-proposed by the unchanged state: shown once
                continue
            seen[op[1]] = key
            lines.append(f"- `s{tr['seq']}` 연산 {op[0]} `{op[1]}` · 근거 찾기 {op[2]} · 판정 **{op[3]}** {op[4]}")
    lines += ["- (상태가 그대로라 같은 연산이 다음 턴에 다시 제안된 경우는 한 번만 적었다.)",
              f"- 결제 전 판정 힌트: **{res['hint']}**, 대기 {res['pending']}, 경보 {res['flags']}", "",
              "## 4. Mandate 생성과 서명 (검증된 장부만 서명, ECDSA P-256)"]
    body = {"ledger": {e.id: (list(e.value) if isinstance(e.value, tuple) else e.value) for e in res["ledger"].entries},
            "pending": res["pending"], "episode": EP}
    sk = new_signing_key()
    sig = sign(sk, body)
    lines += [f"- mandate 본문: `{json.dumps(body, ensure_ascii=False)}`",
              f"- 본문 sha256: `{sha256_hex(body)[:16]}…`, 서명 `{sig[:24]}…`, 공개키 검증 {verify(public_of(sk), body, sig)}",
              "- 대기 항목이 있으면 사용자 확인 전에는 결제 권한을 발급하지 않는다(CLARIFY).", "",
              "## 5. M2 거래 검증 (기록된 장바구니 vs 장부)과 비교군"]
    rn = run_verified(fn, users, nli=NLI())
    lines.append("- fnctod_rn(규칙 + NLI) 근거 찾기: " + "; ".join(
        f"`s{tr['seq']}` {op[0]} `{op[1]}` {op[2]} → {op[3]}" for tr in rn["trace"] for op in tr["ops"]
        if op[1] == "qty" and tr["seq"] == 2))
    arms = {"fnctod (검증 없음)": (plain_led, "OK"), "fnctod_r (FnCTOD + M1 규칙)": (res["ledger"], res["hint"]),
            "fnctod_rn (+ NLI)": (rn["ledger"], rn["hint"])}
    lines.append("| 비교군 | 서명되는 장부 | M1 힌트 | M2 장바구니 검사 | 최종 |")
    lines.append("|---|---|---|---|---|")
    for name, (led, hint) in arms.items():
        d, codes = cart_check(led, cart)
        final = "DENY" if d == "DENY" else ("CLARIFY" if hint == "CLARIFY" else d)
        lines.append(f"| {name} | {json.dumps({e.field: (list(e.value) if isinstance(e.value, tuple) else e.value) for e in led.entries}, ensure_ascii=False)} | {hint} | {d} {codes} | **{final}** |")
    lines += ["", "- 실제 쇼핑객은 이 장바구니를 결제 단계에서 거절했다(`s78`). 정답 동작은 ALLOW가 아니다.",
              "- fnctod는 모호한 고르기를 묶음 철회로 받아들여 헬멧만 담은 장바구니를 ALLOW한다.",
              "- fnctod_r: `s63`의 \"I'll go with Helmet.\"은 고르기일 뿐 철회 단서(WIDEN_CUES)가 없다. 그래서 묶음 철회를 받아들이지 않고, "
              "묶음이 남은 장부로 장바구니를 검사해 빠진 품목(BUNDLE_MEMBER_MISSING)으로 막는다.",
              "- fnctod_r 장부에 수량이 빠진 것은 규칙 근거 찾기가 실패했기 때문이다(아래 6절).", "",
              "## 6. 이 사례에서 드러난 한계 (그대로 적음)",
              "- 수량: FnCTOD가 낸 값 2(총 개수)를 사용자 표현 \"one of each\"에서 규칙으로 찾지 못해 장부에서 빠졌다. NLI 팔 결과는 5절 표에 있다(이 한 사례만 보고, 일반화하지 않는다).",
              "- 2026-11-26 이 사례를 돌리다 규칙 두 개를 고쳤다(validation 사례, 시험 분할 아님): "
              "\"collect it in store\"를 매장 수령으로 인식, \"If it is out of stock, just tell me\"를 조건부 대체 허용으로 읽지 않음. "
              "누락 검사 재실행 결과: `results/omission_realtext_20261126/summary_*_v3_rulefix.json`."]
    out = ROOT / "docs" / f"WALKTHROUGH_{EP}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines[-14:]))


if __name__ == "__main__":
    main()
