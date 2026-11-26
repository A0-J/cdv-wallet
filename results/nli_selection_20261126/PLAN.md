# 계획: V-B·V-X용 NLI 모델 선정 (계산 전에 작성)

- 작성: 2026-11-26 밤
- 유료 호출: 0. 로컬 CPU에서 모델을 실행한다(연구자 승인: CPU NLI 설치).
- 코드: `eval/nli/select_nli.py`(`.venv`, torch 2.15 CPU, transformers 5.24)

## 범위

- **NLI는 V-B(발화가 조건을 말하는가)와 V-X(두 조건 진술이 모순인가)에만 쓴다.** V-C(변경의 정당성)는 판정하지 않는다. 정당성은 출처, 비대칭 단서, 값 진술의 결정적 규칙이 판정한다(`cdv/m1.py`).

## 후보

| 모델 | 라이선스 | 비고 |
|---|---|---|
| `cross-encoder/nli-deberta-v3-base` | Apache-2.0 | 라벨은 `id2label`로 읽는다 |
| `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | MIT | 라벨은 `id2label`로 읽는다 |
| MiniCheck-FT5, AlignScore | Apache-2.0 / MIT | 각자 저장소의 추론 코드(별도 패키지)가 필요하다. 이번에는 설치하지 않고 보류한다. 이유는 결과 문서에 적는다 |

## 데이터 (실제 전제 + 생성 가설)

- **전제:** CartTrace 쇼핑객 첫 발화 원문
  - 개발: validation
  - 평가: test_cross_store(사후 표시)
- **가설:** 숨은 사양의 stated 조건을 고정 문장으로 바꾼 것
  - 정상(뒷받침됨): 사양 값 그대로
  - 비정상(뒷받침 안 됨, 모순): 값을 바꾼 것

| 필드 | 정상 가설 | 바꾼 가설 |
|---|---|---|
| 예산 | "The customer wants to spend at most ${X}." | X × 2 |
| 수량 | "The customer wants {N} items." | N + 2 |
| 조건부 대체 | "The customer accepts a similar item if the requested one is out of stock." | "The customer does not accept any substitute if the requested one is out of stock." |
| 배송 기한 | "The customer needs delivery within {D} days." | D + 20 |
| 수령 | "The customer will collect the order from the store." / "The customer wants the order shipped." | 반대 수령 방식 |

- 표본: 분할마다 필드당 정상 40 + 비정상 40(시드 20261127). 첫 발화에 그 조건이 stated인 여정만 쓴다.

## 지표

- **V-B**
  - 정상 가설을 함의(entailment)로 판정한 비율(근거 재현율)
  - 비정상 가설을 함의로 판정한 비율(거짓 근거율, 낮을수록 좋음)
- **V-X:** 비정상 가설을 모순(contradiction)으로 판정한 비율
- **지연:** 쌍당 CPU 추론 시간(중앙값)
- **선정 기준(개발용에서만 판단):** 거짓 근거율 5% 이하 중 근거 재현율이 가장 높은 모델. 둘 다 기준을 넘으면 거짓 근거율이 낮은 모델을 고른다. 평가용은 선정 뒤 한 번만 계산한다.

## 한계

- 가설 문장이 생성(고정 템플릿)이다. 실제 추출기가 만든 조건 문장에서의 정확도는 E-M1에서 잰다.
- 전제는 시뮬레이터 쇼핑객의 문장이다.

---

## 선정 기록 (개발용 결과를 본 뒤, 평가용 계산 전에 작성)

- 개발(validation, 필드 5개 × 정상 40 + 비정상 40)
  - `cross-encoder/nli-deberta-v3-base`: 근거 재현율 65.0%, 거짓 근거율 5.5%(기준 초과), 바꾼 값 모순 판정 57.5%, 쌍당 52.6ms
  - `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`: 근거 재현율 79.5%, 거짓 근거율 1.0%, 모순 판정 53.0%, 쌍당 351.7ms
- **선정: `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`.** 거짓 근거율 5% 이하인 후보 중 하나뿐이다.
- 평가용(test_cross_store)은 두 모델 모두 한 번 계산해 보고한다. 선정은 바꾸지 않는다.
