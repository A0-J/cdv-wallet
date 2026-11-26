# 최종 평가 데이터 v4b 수령 기록 (모델 호출 0, 대화 문장 미열람)

- 결정(2026-11-27): 최종 평가 데이터는 `carttrace_cdv_evaluation_v4b`. 고정 커밋 610a97c 이후에 받았다는 사실과 시각을 남긴다. 이후 프롬프트와 규칙은 고치지 않는다.

## 시각

| 사건 | 시각 (KST) | 근거 |
|---|---|---|
| 정책 고정 커밋 `610a97c955914ff08d9627a22b549e731366e8ac` | 2026-11-27 00:04:47 | `git log` 커밋 시각 |
| v4b ZIP 내려받기(파일 수정 시각) | 2026-11-27 00:08:40 | `G:\다른 컴퓨터\내 PC\Downloads\carttrace_cdv_evaluation_v4b.zip` 파일 시각 |
| 연구자가 경로를 알려 줌, 압축 해제 | 2026-11-27 00:37 무렵 | 이 세션 |
| ZIP 안 파일 시각 | 2026-11-26 15:06 (시간대 정보 없음) | ZIP 항목. UTC라면 11-27 00:06 KST로 고정 커밋 약 2분 뒤다. 시간대를 확인할 수 없어 근거로 쓰지 않는다 |

## 무결성

- ZIP sha256 `a8b960106474e517ab0c0a35378ae37514cb321fad391db7b28d78300d70c5a3` (결정에 적힌 앞자리 `a8b960106474e517…`와 일치), 크기 1,416,827바이트.
- 압축 해제 위치: `C:\ct\external\carttrace_cdv_evaluation_v4b` (새 폴더, 경로 검사 후 해제).
- `manifest.json`의 파일 sha256 17개 모두 일치.
- `dev/` 6개 파일은 기존 v4 dev와 바이트 단위로 같다(sha256 비교). 따라서 dev 결과는 그대로 유효하다.

## 포함된 코드

- `check_dataset.py` 1개(sha256 `f3426dbe…`, manifest와 일치). 읽어 본 결과 파일을 읽어 집계만 출력한다(네트워크·쓰기 없음). `python -I`로 폴더 밖에서 실행했다.
- 출력(대화 문장 없음, 집계만):
  - eval 변경 후보 959 (수용 418 / 확인 202 / 거부 339)
  - 대화를 읽지 않는 지름길(dev로 학습, eval에 적용): 최다 43.6%, 연산+필드 48.9%, 근거 턴 발화자 60.0%, 셋 결합 60.0%
  - 목록 이후 턴 배열이 dev와 같은 eval 대화 34 / 868, 가린 문장이 dev와 겹치는 턴 0 / 2,747
  - 사용자 턴에 SKU·파이썬 리터럴 0, 매칭 참조 판정 ALLOW 102 / DENY 51 / CLARIFY 51

## 열지 않은 것

- `human_validation/answer_key_changes_do_not_share.csv`, `human_validation/answer_key_payments_do_not_share.csv`: 사람 검증의 정답 키. 평가자(연구자)가 보지 않도록 열지 않았고 내용을 출력하지 않았다. 평가지는 `rater_sheet_changes.csv`, `rater_sheet_payments.csv`.
- eval 대화 문장. 실행 계획 승인 전에는 집계·드라이런 외에 읽지 않는다.
