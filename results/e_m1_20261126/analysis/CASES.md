# E-M1 대표 사례 (자동 선정, 규칙: 각 세트에서 조건을 만족하는 첫 여정)

> [실제 데이터 · 실제 모델 출력]. CartTrace 발화는 CC BY 4.0(generalmachines/CartTrace-100k), 짧게 발췌.

## 성공: 검증 없는 FnCTOD는 통과시킨 위반 거래를 M1이 막음 — R1 실제 일반 여정 `ep-b92c12a726de` (결과 WRONG)

- 사용자 발화: `s6` Same SOLIMO(ソリモ) shampoo as last time, 2 of them please. / `s40` I would prefer express delivery for this order. / `s56` I would like to confirm the payment and proceed with placing the order for $34.41.
- 정답 사양(채점용): {'brand_out': ["['fragrance']", 'on_ask'], 'brand_in': ['solimo(ソリモ)', 'stated'], 'budget_max': [20.0, 'on_ask'], 'quantity': [2, 'stated'], 'fulfillment': ['ship', 'on_ask']}
- FnCTOD 최종 상태: {"set_purchase_conditions": {"product_type": "shampoo", "brand_include": ["SOLIMO"], "quantity": 2, "fulfillment": "ship"}}
- 일반 LLM: 판정 **ALLOW** · 장부 {"quantity": 2, "brand_in": ["SOLIMO"], "fulfillment": "ship", "product_type": "shampoo"} · 경보 [] · 결제 검사 []
- FnCTOD: 판정 **ALLOW** · 장부 {"quantity": 2, "brand_in": ["SOLIMO"], "fulfillment": "ship", "product_type": "shampoo"} · 경보 [] · 결제 검사 []
- FnCTOD+규칙: 판정 **CLARIFY** · 장부 {"brand_in": ["SOLIMO"], "product_type": "shampoo", "quantity": 2} · 경보 ['OMITTED_DEADLINE:s40'] · 결제 검사 []
- FnCTOD+규칙+NLI: 판정 **CLARIFY** · 장부 {"brand_in": ["SOLIMO"], "product_type": "shampoo", "quantity": 2, "fulfillment": "ship"} · 경보 ['OMITTED_DEADLINE:s40'] · 결제 검사 []
- M1(규칙)이 받아들이지 않은 연산: `s40` add ful (none) → REJECT ['NON_USER_SOURCE']; `s56` add ful (none) → REJECT ['NON_USER_SOURCE']

## 성공: 근거 없는 조건을 장부에서 빼고 정상 거래는 통과 — R1 실제 일반 여정 `ep-0faab697a457` (결과 RIGHT)

- 사용자 발화: `s6` No need to show me options: just order a sticker. I'd rather collect it in store. / `s37` Yes, go ahead and place the order for $4.85.
- 정답 사양(채점용): {'fulfillment': ['pickup', 'stated']}
- FnCTOD 최종 상태: {"set_purchase_conditions": {"product_type": "sticker", "quantity": 1, "fulfillment": "pickup"}}
- 일반 LLM: 판정 **ALLOW** · 장부 {"quantity": 1, "fulfillment": "pickup", "product_type": "sticker"} · 경보 [] · 결제 검사 []
- FnCTOD: 판정 **ALLOW** · 장부 {"quantity": 1, "fulfillment": "pickup", "product_type": "sticker"} · 경보 [] · 결제 검사 []
- FnCTOD+규칙: 판정 **ALLOW** · 장부 {"fulfillment": "pickup", "product_type": "sticker"} · 경보 [] · 결제 검사 []
- FnCTOD+규칙+NLI: 판정 **ALLOW** · 장부 {"fulfillment": "pickup", "product_type": "sticker"} · 경보 [] · 결제 검사 []
- M1(규칙)이 받아들이지 않은 연산: `s6` add qty (none) → REJECT ['NON_USER_SOURCE']; `s37` add qty (none) → REJECT ['NON_USER_SOURCE']

## 실패: 정상 거래를 막거나 확인 요청(오차단) — R1 실제 일반 여정 `ep-7c79cb434298` (결과 RIGHT)

- 사용자 발화: `s2` Can I get the Baby Bracelet? If it's out of stock, something similar from your range will do. Standard shipping works for me. / `s42` I'm so sorry, I don't have that information to hand right now. Could you ask me again in a moment? / `s46` Yes, that one sounds right. Please go ahead with it. / `s66` Thanks so much for your patience! Yes, please go ahead and place the order for $135.58.
- 정답 사양(채점용): {'substitute': [True, 'stated'], 'fulfillment': ['ship', 'stated']}
- FnCTOD 최종 상태: {"set_purchase_conditions": {"budget_max": 135.58, "quantity": 1, "product_type": "Hematite Bracelet (Blessed Already)", "fulfillment": "ship"}, "set_substitution_policy": {"allowed": true, "scope": "named", "named_alternatives": ["Hematite Bracelet (Blessed Already)"]}}
- 일반 LLM: 판정 **ALLOW** · 장부 {"fulfillment": "ship", "product_type": "bracelet", "substitute": null} · 경보 [] · 결제 검사 []
- FnCTOD: 판정 **ALLOW** · 장부 {"budget_max": 135.58, "quantity": 1, "fulfillment": "ship", "product_type": "Hematite Bracelet (Blessed Already)", "substitute": null} · 경보 [] · 결제 검사 []
- FnCTOD+규칙: 판정 **CLARIFY** · 장부 {"product_type": "Baby Bracelet", "substitute": null} · 경보 [] · 결제 검사 []
- FnCTOD+규칙+NLI: 판정 **CLARIFY** · 장부 {"fulfillment": "ship", "product_type": "Baby Bracelet", "substitute": null} · 경보 [] · 결제 검사 []
- M1(규칙)이 받아들이지 않은 연산: `s2` add ful (none) → REJECT ['NON_USER_SOURCE']; `s42` add ful (none) → REJECT ['NON_USER_SOURCE']; `s46` add ful (none) → REJECT ['NON_USER_SOURCE']; `s46` override ptype (rule) → PENDING ['WIDEN_WITHOUT_EXPLICIT_CUE']; `s46` override sub (rule) → PENDING ['WIDEN_WITHOUT_EXPLICIT_CUE']; `s66` add budget (none) → REJECT ['NON_USER_SOURCE']; `s66` add ful (none) → REJECT ['NON_USER_SOURCE']; `s66` override ptype (rule) → PENDING ['WIDEN_WITHOUT_EXPLICIT_CUE']; `s66` add qty (none) → REJECT ['NON_USER_SOURCE']; `s66` override sub (rule) → PENDING ['WIDEN_WITHOUT_EXPLICIT_CUE']

## 실패: 모든 팔과 상한(정답 장부)도 통과시킨 위반 거래 — R1 실제 일반 여정 `ep-e4c504fdd1c0` (결과 WRONG)

- 사용자 발화: `s4` Do you have a patio bar stool under $70 all in, with shipping?
- 정답 사양(채점용): {'budget_max': [70.0, 'stated'], 'fulfillment': ['ship', 'on_ask']}
- FnCTOD 최종 상태: {"set_purchase_conditions": {"budget_max": 70, "product_type": "patio bar stool", "fulfillment": "ship"}}
- 일반 LLM: 판정 **ALLOW** · 장부 {"budget_max": 70.0, "fulfillment": "ship", "product_type": "patio bar stool"} · 경보 [] · 결제 검사 []
- FnCTOD: 판정 **ALLOW** · 장부 {"budget_max": 70.0, "fulfillment": "ship", "product_type": "patio bar stool"} · 경보 [] · 결제 검사 []
- FnCTOD+규칙: 판정 **ALLOW** · 장부 {"budget_max": 70.0, "product_type": "patio bar stool"} · 경보 [] · 결제 검사 []
- FnCTOD+규칙+NLI: 판정 **ALLOW** · 장부 {"budget_max": 70.0, "fulfillment": "ship", "product_type": "patio bar stool"} · 경보 [] · 결제 검사 []
- M1(규칙)이 받아들이지 않은 연산: `s4` add ful (none) → REJECT ['NON_USER_SOURCE']

## 성공: 검증 없는 FnCTOD는 통과시킨 위반 거래를 M1이 막음 — R3 조건부 대체 + 실제 품절 `ep-5f1bf6ab9dda` (결과 WRONG)

- 사용자 발화: `s1` I'm running low on the Fudgee Barr Milk. / `s21` Oh no, that's a shame. In that case, I'm perfectly happy to try something similar from your range if you've got a recommendation. / `s56` I'm so sorry, but I don't have that information to hand right now. Would you mind asking me again in a moment? / `s59` No allergies I need to worry about. Thanks for your patience! / `s62` Just to be clear, I really don't have any allergies to worry about. / `s65` I know I keep coming back to it, but just to repeat: no allergies I need to worry about.
- 정답 사양(채점용): {'substitute': [True, 'stated'], 'fulfillment': ['pickup', 'on_ask']}
- FnCTOD 최종 상태: {"set_purchase_conditions": {"budget_max": 2.49, "quantity": 1, "product_type": "Happy Belly Honey Graham Crackers"}, "set_substitution_policy": {"allowed": true, "scope": "closest", "named_alternatives": []}}
- 일반 LLM: 판정 **ALLOW** · 장부 {"product_type": "sweet, cake-like snack", "substitute": null} · 경보 [] · 결제 검사 []
- FnCTOD: 판정 **ALLOW** · 장부 {"budget_max": 2.49, "quantity": 1, "product_type": "Happy Belly Honey Graham Crackers", "substitute": null} · 경보 [] · 결제 검사 []
- FnCTOD+규칙: 판정 **CLARIFY** · 장부 {"product_type": "Fudgee Barr Milk"} · 경보 [] · 결제 검사 []
- FnCTOD+규칙+NLI: 판정 **CLARIFY** · 장부 {"product_type": "Fudgee Barr Milk"} · 경보 [] · 결제 검사 []
- M1(규칙)이 받아들이지 않은 연산: `s21` add_substitute sub (none) → REJECT ['NON_USER_SOURCE']; `s56` add_substitute sub (none) → REJECT ['NON_USER_SOURCE']; `s59` add_substitute sub (none) → REJECT ['NON_USER_SOURCE']; `s62` add_substitute sub (none) → REJECT ['NON_USER_SOURCE']; `s65` add_substitute sub (none) → REJECT ['NON_USER_SOURCE']; `s72` add budget (none) → REJECT ['NON_USER_SOURCE']; `s72` override ptype (rule) → PENDING ['WIDEN_WITHOUT_EXPLICIT_CUE']; `s72` add qty (none) → REJECT ['NON_USER_SOURCE']; `s72` add_substitute sub (none) → REJECT ['NON_USER_SOURCE']

## 성공: 근거 없는 조건을 장부에서 빼고 정상 거래는 통과 — R3 조건부 대체 + 실제 품절 `ep-e86a7fc26faa` (결과 RIGHT)

- 사용자 발화: `s4` Please order the AmazonBasics No-Stud Heavy-Duty Tilting TV Wall Mount for 32-inch to 80-inch TVs with 80-inch Velcro Cable for me. If it's 
- 정답 사양(채점용): {'substitute': [True, 'stated'], 'fulfillment': ['ship', 'on_ask']}
- FnCTOD 최종 상태: {"set_purchase_conditions": {"quantity": 1, "product_type": "AmazonBasics No-Stud Heavy-Duty Tilting TV Wall Mount for 32-inch to 80-inch TVs with 80-inch Velcro Cable; if unavailable, a similar item from the available range"}, "set_substitution_policy": {"allowed": true, "scope": "closest"}}
- 일반 LLM: 판정 **DENY** · 장부 {"brand_in": ["AmazonBasics"], "bundle_all": ["fits 32-inch to 80-inch TVs", "80-inch Velcro cable"], "product_type": "tilting TV wall mount", "substitute": null} · 경보 [] · 결제 검사 ['BUNDLE_MEMBER_MISSING']
- FnCTOD: 판정 **ALLOW** · 장부 {"quantity": 1, "product_type": "AmazonBasics No-Stud Heavy-Duty Tilting TV Wall Mount for 32-inch to 80-inch TVs with 80-inch Velcro Cable; if unavailable, a similar item from the available range", "substitute": null} · 경보 [] · 결제 검사 []
- FnCTOD+규칙: 판정 **ALLOW** · 장부 {"product_type": "AmazonBasics No-Stud Heavy-Duty Tilting TV Wall Mount for 32-inch to 80-inch TVs with 80-inch Velcro Cable; if unavailable, a similar item from the available range", "substitute": null} · 경보 [] · 결제 검사 []
- FnCTOD+규칙+NLI: 판정 **ALLOW** · 장부 {"product_type": "AmazonBasics No-Stud Heavy-Duty Tilting TV Wall Mount for 32-inch to 80-inch TVs with 80-inch Velcro Cable; if unavailable, a similar item from the available range", "substitute": null} · 경보 [] · 결제 검사 []
- M1(규칙)이 받아들이지 않은 연산: `s4` add qty (none) → REJECT ['NON_USER_SOURCE']

## 실패: 정상 거래를 막거나 확인 요청(오차단) — R3 조건부 대체 + 실제 품절 `ep-12b745a6aa48` (결과 RIGHT)

- 사용자 발화: `s2` I'm after the find. Men's Leather Chelsea Boots again. If it's out of stock, something similar from your range will do. Standard delivery is / `s25` I'll take the find. Men's Chelsea Boots, Grau (Anthracite Suede Look). / `s39` Yes. Place the order for $86.39.
- 정답 사양(채점용): {'substitute': [True, 'stated'], 'fulfillment': ['ship', 'stated']}
- FnCTOD 최종 상태: {"set_purchase_conditions": {"product_type": "find. Men's Chelsea Boots, Grau (Anthracite Suede Look)", "fulfillment": "ship"}, "set_substitution_policy": {"allowed": true, "scope": "named", "named_alternatives": ["find. Men's Chelsea Boots, Grau (Anthracite Suede Look)"]}}
- 일반 LLM: 판정 **ALLOW** · 장부 {"quantity": 1, "brand_in": ["find."], "fulfillment": "ship", "product_type": "Men's Chelsea boots", "substitute": null} · 경보 [] · 결제 검사 []
- FnCTOD: 판정 **ALLOW** · 장부 {"fulfillment": "ship", "product_type": "find. Men's Chelsea Boots, Grau (Anthracite Suede Look)", "substitute": null} · 경보 [] · 결제 검사 []
- FnCTOD+규칙: 판정 **CLARIFY** · 장부 {"fulfillment": "ship", "product_type": "Men's Leather Chelsea Boots", "substitute": null} · 경보 [] · 결제 검사 []
- FnCTOD+규칙+NLI: 판정 **CLARIFY** · 장부 {"fulfillment": "ship", "product_type": "Men's Leather Chelsea Boots", "substitute": null} · 경보 [] · 결제 검사 []
- M1(규칙)이 받아들이지 않은 연산: `s25` override ptype (rule) → PENDING ['WIDEN_WITHOUT_EXPLICIT_CUE']; `s25` override sub (rule) → PENDING ['WIDEN_WITHOUT_EXPLICIT_CUE']; `s39` override ptype (rule) → PENDING ['WIDEN_WITHOUT_EXPLICIT_CUE']; `s39` override sub (rule) → PENDING ['WIDEN_WITHOUT_EXPLICIT_CUE']

## 실패: 모든 팔과 상한(정답 장부)도 통과시킨 위반 거래 — R3 조건부 대체 + 실제 품절 `ep-f7ac78bc138b` (결과 WRONG)

- 사용자 발화: `s1` I'm after the Furniture TV Rack again. If it's out of stock, something similar from your range will do.
- 정답 사양(채점용): {'substitute': [True, 'stated'], 'fulfillment': ['ship', 'on_ask'], 'deadline_days': [7, 'on_ask']}
- FnCTOD 최종 상태: {"set_purchase_conditions": {"product_type": "Furniture TV Rack"}, "set_substitution_policy": {"allowed": true, "scope": "closest"}}
- 일반 LLM: 판정 **ALLOW** · 장부 {"product_type": "Furniture TV Rack", "substitute": null} · 경보 [] · 결제 검사 []
- FnCTOD: 판정 **ALLOW** · 장부 {"product_type": "Furniture TV Rack", "substitute": null} · 경보 [] · 결제 검사 []
- FnCTOD+규칙: 판정 **ALLOW** · 장부 {"product_type": "Furniture TV Rack", "substitute": null} · 경보 [] · 결제 검사 []
- FnCTOD+규칙+NLI: 판정 **ALLOW** · 장부 {"product_type": "Furniture TV Rack", "substitute": null} · 경보 [] · 결제 검사 []

## 성공: 검증 없는 FnCTOD는 통과시킨 위반 거래를 M1이 막음 — R2 품절 → 고르기 → 거절 (의도 불명확) `ep-02e255278e7e` (결과 WRONG_HIDDEN)

- 사용자 발화: `s3` Can I get the RRJ Men's T-shirt? I'll collect it from the store. / `s28` Thank you for checking. I am looking for a t-shirt. / `s36` I would like to proceed with option 2, the Training sleeveless quick-dry tank top. / `s41` I have no preference regarding the colour. I also have no preference as to the size. / `s76` I apologize, but that is not the item I requested, so please do not place the order. As I mentioned previously, I am only interested in the 
- 정답 사양(채점용): {'substitute': [True, 'stated'], 'fulfillment': ['pickup', 'stated']}
- FnCTOD 최종 상태: {"set_purchase_conditions": {"product_type": "RRJ Men's T-shirt", "fulfillment": "pickup"}, "set_substitution_policy": {"allowed": false, "scope": "named", "named_alternatives": []}}
- 일반 LLM: 판정 **DENY** · 장부 {"brand_in": ["RRJ"], "fulfillment": "pickup", "product_type": "T-shirt"} · 경보 [] · 결제 검사 ['BRAND_NOT_ALLOWED']
- FnCTOD: 판정 **ALLOW** · 장부 {"fulfillment": "pickup", "product_type": "RRJ Men's T-shirt"} · 경보 [] · 결제 검사 []
- FnCTOD+규칙: 판정 **CLARIFY** · 장부 {"fulfillment": "pickup", "product_type": "RRJ Men's T-shirt"} · 경보 [] · 결제 검사 []
- FnCTOD+규칙+NLI: 판정 **CLARIFY** · 장부 {"fulfillment": "pickup", "product_type": "RRJ Men's T-shirt"} · 경보 [] · 결제 검사 []
- M1(규칙)이 받아들이지 않은 연산: `s28` override ptype (rule) → PENDING ['WIDEN_WITHOUT_EXPLICIT_CUE']; `s36` override ptype (rule) → PENDING ['WIDEN_WITHOUT_EXPLICIT_CUE']; `s41` override ptype (rule) → PENDING ['WIDEN_WITHOUT_EXPLICIT_CUE']

## 성공: 근거 없는 조건을 장부에서 빼고 정상 거래는 통과 — R2 품절 → 고르기 → 거절 (의도 불명확) `ep-05afeab55b39` (결과 RIGHT)

- 사용자 발화: `s2` I need a gift for my father: a recliner. I'd like to have it within 8 days, so the standard delivery option is fine. / `s50` Oh, that one sounds right! Please go ahead with it, and thank you so much for your help. / `s92` Please ship it to Mateo Vexley, 44 Bramble Drive, Springfield, IL 62739, US. No preference on the returns. / `s114` That isn't the item I asked for, so please don't place the order. Like I said, I'm looking for a recliner. / `s126` Yes, that one sounds right, so please go ahead with it. Thanks for sorting that out for me! / `s129` Go for Light Pink, please. Thanks a million for your help!
- 정답 사양(채점용): {'fulfillment': ['ship', 'stated'], 'deadline_days': [8, 'stated']}
- FnCTOD 최종 상태: {"set_purchase_conditions": {"budget_max": 653.39, "quantity": 1, "product_type": "recliner", "brand_include": ["AmazonBasics"], "deadline_days": 8, "fulfillment": "ship"}, "set_substitution_policy": {"allowed": false}}
- 일반 LLM: 판정 **ALLOW** · 장부 {"quantity": 1, "deadline_days": 8, "fulfillment": "ship", "product_type": "recliner"} · 경보 [] · 결제 검사 []
- FnCTOD: 판정 **ALLOW** · 장부 {"budget_max": 653.39, "quantity": 1, "brand_in": ["AmazonBasics"], "deadline_days": 8, "fulfillment": "ship", "product_type": "recliner"} · 경보 [] · 결제 검사 []
- FnCTOD+규칙: 판정 **ALLOW** · 장부 {"deadline_days": 8, "fulfillment": "ship", "product_type": "recliner"} · 경보 [] · 결제 검사 []
- FnCTOD+규칙+NLI: 판정 **CLARIFY** · 장부 {"deadline_days": 8, "fulfillment": "ship", "product_type": "recliner"} · 경보 [] · 결제 검사 []
- M1(규칙)이 받아들이지 않은 연산: `s92` override ptype (none) → REJECT ['NON_USER_SOURCE']; `s92` add qty (none) → REJECT ['NON_USER_SOURCE']; `s114` add qty (none) → REJECT ['NON_USER_SOURCE']; `s126` add qty (none) → REJECT ['NON_USER_SOURCE']; `s129` add brand_in (none) → REJECT ['NON_USER_SOURCE']; `s129` add qty (none) → REJECT ['NON_USER_SOURCE']; `s163` add brand_in (none) → REJECT ['NON_USER_SOURCE']; `s163` add budget (none) → REJECT ['NON_USER_SOURCE']; `s163` add qty (none) → REJECT ['NON_USER_SOURCE']; `s183` add brand_in (none) → REJECT ['NON_USER_SOURCE']; `s183` add budget (none) → REJECT ['NON_USER_SOURCE']; `s183` add qty (none) → REJECT ['NON_USER_SOURCE']; `s187` add brand_in (none) → REJECT ['NON_USER_SOURCE']; `s187` add budget (none) → REJECT ['NON_USER_SOURCE']; `s187` add qty (none) → REJECT ['NON_USER_SOURCE']

## 실패: 정상 거래를 막거나 확인 요청(오차단) — R2 품절 → 고르기 → 거절 (의도 불명확) `ep-0aec68ad85b2` (결과 RIGHT)

- 사용자 발화: `s3` My budget for the Floor Cleaning Brushes is $70. Please buy as many as it covers, and nothing more. / `s16` I’ll go with one of each, please. Thanks! / `s43` Standard shipping works for me. My email address is email-d8a33f62c5ed@redacted.invalid. / `s54` Standard shipping works for me. Please ship it to Imani Marrowby, 65 Lantern Street, Albany, NY 12265, US. / `s72` I only want the one item I asked for, so please don't place the order with anything else. / `s78` I'm feeling a bit unsure about all those details, so please just go with whatever fits what I've already told you.
- 정답 사양(채점용): {'budget_max': [70.0, 'stated'], 'quantity': [2, 'stated'], 'fulfillment': ['ship', 'on_ask']}
- FnCTOD 최종 상태: {"set_purchase_conditions": {"budget_max": 70, "quantity": 2, "product_type": "Floor Cleaning Brushes", "deadline_days": 7, "fulfillment": "ship"}, "set_substitution_policy": {"allowed": false, "scope": "named", "named_alternatives": []}}
- 일반 LLM: 판정 **ALLOW** · 장부 {"budget_max": 70.0, "quantity": 2, "fulfillment": "ship", "product_type": "Floor Cleaning Brushes (the originally requested product only)"} · 경보 [] · 결제 검사 []
- FnCTOD: 판정 **ALLOW** · 장부 {"budget_max": 70.0, "quantity": 2, "deadline_days": 7, "fulfillment": "ship", "product_type": "Floor Cleaning Brushes"} · 경보 [] · 결제 검사 []
- FnCTOD+규칙: 판정 **CLARIFY** · 장부 {"product_type": "Floor Cleaning Brushes", "fulfillment": "ship"} · 경보 ['OMITTED_BUNDLE:s16'] · 결제 검사 []
- FnCTOD+규칙+NLI: 판정 **CLARIFY** · 장부 {"budget_max": 70.0, "product_type": "Floor Cleaning Brushes", "fulfillment": "ship"} · 경보 ['OMITTED_BUNDLE:s16'] · 결제 검사 []
- M1(규칙)이 받아들이지 않은 연산: `s3` add budget (none) → REJECT ['NON_USER_SOURCE']; `s16` add budget (none) → REJECT ['NON_USER_SOURCE']; `s16` add qty (none) → REJECT ['NON_USER_SOURCE']; `s43` add budget (none) → REJECT ['NON_USER_SOURCE']; `s43` add ful (none) → REJECT ['NON_USER_SOURCE']; `s43` add qty (none) → REJECT ['NON_USER_SOURCE']; `s54` add budget (none) → REJECT ['NON_USER_SOURCE']; `s54` add qty (none) → REJECT ['NON_USER_SOURCE']; `s72` add budget (none) → REJECT ['NON_USER_SOURCE']; `s72` add qty (none) → REJECT ['NON_USER_SOURCE']; `s78` add budget (none) → REJECT ['NON_USER_SOURCE']; `s78` add qty (none) → REJECT ['NON_USER_SOURCE']; `s82` add budget (none) → REJECT ['NON_USER_SOURCE']; `s82` add qty (none) → REJECT ['NON_USER_SOURCE']; `s90` add budget (none) → REJECT ['NON_USER_SOURCE']; `s90` add qty (none) → REJECT ['NON_USER_SOURCE']; `s96` add budget (none) → REJECT ['NON_USER_SOURCE']; `s96` add deadline (none) → REJECT ['NON_USER_SOURCE']; `s96` add qty (none) → REJECT ['NON_USER_SOURCE']; `s107` add budget (none) → REJECT ['NON_USER_SOURCE']; `s107` add deadline (none) → REJECT ['NON_USER_SOURCE']; `s107` add qty (none) → REJECT ['NON_USER_SOURCE']; `s132` add budget (none) → REJECT ['NON_USER_SOURCE']; `s132` add deadline (none) → REJECT ['NON_USER_SOURCE']; `s132` add qty (none) → REJECT ['NON_USER_SOURCE']; `s137` add budget (none) → REJECT ['NON_USER_SOURCE']; `s137` add deadline (none) → REJECT ['NON_USER_SOURCE']; `s137` add qty (none) → REJECT ['NON_USER_SOURCE']; `s141` add budget (none) → REJECT ['NON_USER_SOURCE']; `s141` add deadline (none) → REJECT ['NON_USER_SOURCE']; `s141` add qty (none) → REJECT ['NON_USER_SOURCE']; `s146` add budget (none) → REJECT ['NON_USER_SOURCE']; `s146` add deadline (none) → REJECT ['NON_USER_SOURCE']; `s146` add qty (none) → REJECT ['NON_USER_SOURCE']; `s150` add budget (none) → REJECT ['NON_USER_SOURCE']; `s150` add deadline (none) → REJECT ['NON_USER_SOURCE']; `s150` add qty (none) → REJECT ['NON_USER_SOURCE']; `s161` add budget (none) → REJECT ['NON_USER_SOURCE']; `s161` add deadline (none) → REJECT ['NON_USER_SOURCE']; `s161` add qty (none) → REJECT ['NON_USER_SOURCE']; `s198` add budget (none) → REJECT ['NON_USER_SOURCE']; `s198` add deadline (none) → REJECT ['NON_USER_SOURCE']; `s198` add qty (none) → REJECT ['NON_USER_SOURCE']; `s198` add_substitute sub (none) → REJECT ['NON_USER_SOURCE']; `s226` add budget (none) → REJECT ['NON_USER_SOURCE']; `s226` add deadline (none) → REJECT ['NON_USER_SOURCE']; `s226` add qty (none) → REJECT ['NON_USER_SOURCE']

## 실패: 모든 팔과 상한(정답 장부)도 통과시킨 위반 거래 — R2 품절 → 고르기 → 거절 (의도 불명확) `ep-c981ab565a16` (결과 WRONG)

- 사용자 발화: `s2` I've narrowed it down to the find. Espadrille Base Sandal and the find. Women's Mule Open-Toe Sandals. I'd like whichever is cheapest. Can y / `s13` I'll go with Color. / `s17` None of those work. I am choosing between the find. Espadrille Base Sandal and the find. Women's Mule Open-Toe Sandals. / `s60` As I mentioned, it has to reach me within 3 days, so I'd like it sent express. / `s79` That isn't the item I asked for, so please don't place the order. It should be the cheapest of them, as I said. / `s84` Doesn't matter which color. Just get me the mule.
- 정답 사양(채점용): {'fulfillment': ['ship', 'stated'], 'deadline_days': [3, 'stated']}
- FnCTOD 최종 상태: {"set_purchase_conditions": {"product_type": "find. Women's Mule Open-Toe Sandals", "brand_include": ["find."], "deadline_days": 3, "fulfillment": "ship"}}
- 일반 LLM: 판정 **ALLOW** · 장부 {"brand_in": ["find."], "deadline_days": 3, "fulfillment": "ship", "product_type": "sandals"} · 경보 [] · 결제 검사 []
- FnCTOD: 판정 **ALLOW** · 장부 {"brand_in": ["find."], "deadline_days": 3, "fulfillment": "ship", "product_type": "find. Women's Mule Open-Toe Sandals"} · 경보 [] · 결제 검사 []
- FnCTOD+규칙: 판정 **ALLOW** · 장부 {"brand_in": ["find."], "deadline_days": 3, "product_type": "find. Women's Mule Open-Toe Sandals"} · 경보 [] · 결제 검사 []
- FnCTOD+규칙+NLI: 판정 **ALLOW** · 장부 {"brand_in": ["find."], "deadline_days": 3, "fulfillment": "ship", "product_type": "find. Women's Mule Open-Toe Sandals"} · 경보 [] · 결제 검사 []
- M1(규칙)이 받아들이지 않은 연산: `s2` add ful (none) → REJECT ['NON_USER_SOURCE']; `s13` add ful (none) → REJECT ['NON_USER_SOURCE']; `s17` add ful (none) → REJECT ['NON_USER_SOURCE']; `s60` add ful (none) → REJECT ['NON_USER_SOURCE']; `s79` add ful (none) → REJECT ['NON_USER_SOURCE']; `s84` add ful (none) → REJECT ['NON_USER_SOURCE']; `s98` add ful (none) → REJECT ['NON_USER_SOURCE']

# G1 대표 사례 — [생성 데이터 · 실제 모델 출력]

## 성공(생성): 모호한 고르기를 묶음 철회로 받아들이지 않음 — `G1-eval-C6_ambiguous_pick_bundle-02`

- 사용자 발화: Could you add the PUMA x TROLLS Kids Boys Hoodie, the sacred Silverette Nursing Cups and the delphine 35 '' bookcase to one order, one of each under $300? / I'll go with the PUMA x TROLLS.
- 외부(판매자) 문장: 없음
- FnCTOD 최종 상태: {"set_purchase_conditions": {"budget_max": 300, "quantity": 1, "product_type": "PUMA x TROLLS Kids Boys Hoodie"}}
- 일반 LLM: 오답 · 힌트 OK
- FnCTOD: 오답 · 힌트 OK
- FnCTOD+규칙: 정답 · 힌트 OK
- FnCTOD+규칙+NLI: 정답 · 힌트 CLARIFY

## 성공(생성): 브랜드 포함·제외 충돌을 확인 요청 — `G1-eval-X3_brand_in_out-00`

- 사용자 발화: I'm putting together two things: the ASUS Micro-ATX Gaming Motherboard and the Notebook. I'd like one of each under $350. I'd prefer express shipping. Anker ple / No Anker please.
- 외부(판매자) 문장: 없음
- FnCTOD 최종 상태: {"set_purchase_conditions": {"budget_max": 350, "quantity": 2, "brand_exclude": ["Anker"], "required_items": ["ASUS Micro-ATX Gaming Motherboard", "Notebook"], "fulfillment": "ship"}}
- 일반 LLM: 오답 · 힌트 OK
- FnCTOD: 오답 · 힌트 OK
- FnCTOD+규칙: 정답 · 힌트 CLARIFY
- FnCTOD+규칙+NLI: 정답 · 힌트 CLARIFY

## 실패(생성): 추출기는 맞았는데 M1이 틀림 — `G1-eval-C2_relax_no_cue-03`

- 사용자 발화: My budget for the Anthurium Yellow Coral is $250. Please buy as many as it covers, and nothing more. / That one looks nice.
- 외부(판매자) 문장: 없음
- FnCTOD 최종 상태: {"set_purchase_conditions": {"budget_max": 250, "product_type": "Anthurium Yellow Coral"}}
- 일반 LLM: 정답 · 힌트 OK
- FnCTOD: 정답 · 힌트 OK
- FnCTOD+규칙: 오답 · 힌트 OK
- FnCTOD+규칙+NLI: 정답 · 힌트 OK

## 실패(생성): 정당한 명시적 묶음 제외를 모든 팔이 반영 못 함 — `G1-eval-C7_explicit_drop_bundle-07`

- 사용자 발화: I'd like the Mama Bear Wide-Neck Baby Bottle, the Disney Girls' School Backpack and the AIBEDILA Newborn Outdoor Sweater together in one order, one of each. / Actually I don't need the Disney D100 Minnie, just the Amazon Brand -.
- 외부(판매자) 문장: 없음
- FnCTOD 최종 상태: {"set_purchase_conditions": {"quantity": 3, "required_items": ["Mama Bear Wide-Neck Baby Bottle", "Amazon Brand -", "AIBEDILA Newborn Outdoor Sweater"]}}
- 일반 LLM: 오답 · 힌트 OK
- FnCTOD: 오답 · 힌트 OK
- FnCTOD+규칙: 오답 · 힌트 CLARIFY
- FnCTOD+규칙+NLI: 오답 · 힌트 CLARIFY

