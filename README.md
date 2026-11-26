# cdv-wallet

에이전트 결제에서 대화 맥락 검증과 권한 검증을 함께 하는 프레임워크(CDV-Wallet)의 구현 저장소다.

- **상태(2026-11-26)**
  - 권한 검증 게이트(ECDSA P-256 서명), M1 결정적 검증(누락 검사 8개 필드)을 구현했다. 시험 49개가 통과한다.
  - 실험 정리(논문용): `docs/EXPERIMENTS.md`
  - 결과: `results/`
    - `whisperbench_e2_20261126`(X1)
    - `g3_whisperbench_20261126`(X2)
    - `omission_realtext_20261126`(X3)
    - `nli_selection_20261126`(X4)
    - `g1_templates_20261126`(X5)
    - `e_m1_20261126`(X7 계획, 승인 대기)
- **실행 환경**
  - `.venv`(git 제외): Python 3.13, cryptography 50, torch 2.15 CPU, transformers 5.24
  - 시험: `.venv\Scripts\python.exe -m pytest -q tests`
  - A-VIP submodule이 없으면 `CDV_AVIP_BINDING`에 `binding` 폴더 경로를 지정한다.
- **비공개 저장소다.** 공개 여부는 논문 제출 때 정한다.
- **설계 문서**
  - 전체 설계: `docs/design/cdv_wallet_design_v2_20261126.md`
  - 권한 검증 어댑터: `docs/ADAPTER_DESIGN.md`
  - 평가 세트 초안: `docs/design/cdv_s2_s3_plan_draft_20261126.md`
- **사전등록과 결과**도 이 저장소의 `results/`에 둔다(2026-11-26 연구자 결정: CDV 관련 자료는 모두 이 폴더에 둔다).

## 구성 (예정)

```
cdv/          제안 기술 (장부, M1 변경 검증, 조건부 조항, 증거 검증, 게이트, 결합)
adapters/     avip.py, standing.py
baselines/    비교군 B0–B8 (원본·재구현 표시)
eval/         CartTrace 게이트 오프라인 재생 (C:\ct를 읽기만 함)
tests/
third_party/  avip_defense, standing-not-truth (submodule, 커밋 고정, 수정 금지)
```

## 규칙

- 데이터(CartTrace, 상품 글, 모델 응답 원문)는 넣지 않는다.
- API 키 파일은 넣지 않는다.
- 모델 호출은 승인된 계획(sha256) 아래에서만 한다.
- 라이선스: Apache 2.0. 외부 저작물은 `NOTICE`를 본다.
