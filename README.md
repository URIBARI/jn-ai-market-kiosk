# 전남AI장터혁신단 — 음성 기반 AI 거래 키오스크 (MVP)

2026년 대학생 무한도전 CES 프로젝트 — 전남AI장터혁신단

에이전틱 AI 음성 UX 기반 전남 고령 농어업인 자율거래 키오스크 MVP 및 농수산 유통 AX 산학협력 모델 제작.

## 프로젝트 개요

고령 농어업인이 음성으로 품목·수량·출하일·희망가격을 말하면, AI가 이를 구조화하고 실시간 도매시세·물류비·수수료를 반영해 추천가격·예상수익·거래 제안서를 자동 생성하는 서비스입니다.

1차 타깃 품목: 무화과, 복숭아, 양파, 부추, 청포도 (전남 특산 신선농산물, 좁은 유통망 직거래 중심)

## 파이프라인

```
음성 입력 → STT(음성인식) → LLM(정보 구조화) → 계산 로직(실시간 데이터 결합) → LLM(문서화) → 거래 제안서
```

- `stt/` : 음성 → 텍스트 변환 모듈 (STT API 연동)
- `llm/` : 텍스트 → 구조화된 정보 추출, 결과 문서화 (LLM API 연동)
- `calc/` : 추천가격·예상수익 계산 로직 (규칙 기반, 실시간 시세 데이터 반영)
- `proposal/` : 거래 제안서 템플릿 및 생성
- `data/` : 외부 데이터 연동 (KAMIS 등 도매시세 API), 캐시
- `tests/` : 테스트 시나리오 및 사용자 테스트 스크립트
- `docs/` : 설계 문서, 회의록, 조사 자료

## 개발 현황

- [ ] 데이터 가용성 확인 (KAMIS 품목 커버리지: 무화과/복숭아/양파/부추/청포도) — API 키 발급 대기 중
- [x] 계산 로직 설계 (직거래 절감액 포함) — `calc/pricing.py`, 상수는 PLACEHOLDER (검증 필요)
- [x] 파이프라인 뼈대 구축 (더미 데이터) — `data/kamis_client.py`(더미 모드) + `calc/pricing.py` 연동, `tests/demo_pipeline.py`로 확인 가능
- [x] LLM 정보 구조화 뼈대 (더미) — `llm/extractor.py`, `llm/schema.py`, STT API 미연동 상태라 '이미 STT를 거친 텍스트'를 입력으로 가정
- [ ] STT/LLM API 실연동
- [x] 거래 제안서 생성 (더미 전체 파이프라인) — `proposal/generator.py`, `tests/demo_full_pipeline.py`로 STT텍스트→LLM구조화→계산→제안서까지 확인 가능
- [ ] 사용자 테스트 (시나리오 6건 이상, 테스트 15회 이상)

### 더미 파이프라인 실행 방법

```
python3 tests/demo_pipeline.py          # data -> calc 더미 파이프라인 데모 출력
python3 tests/demo_llm_pipeline.py      # (텍스트)STT -> LLM 구조화 -> 되물어 확인 -> data/calc 데모
python3 tests/demo_full_pipeline.py     # 전체: STT텍스트 -> LLM 구조화 -> 되물어 확인 -> data/calc -> 거래 제안서
python3 -m unittest discover -s tests   # 단위 테스트 (표준 라이브러리만 사용, pytest 불필요)
```

### LLM 모듈 설계 메모

- `llm/schema.py`의 `TRADE_REQUEST_JSON_SCHEMA`가 STT 텍스트 -> LLM 구조화 출력의 계약(contract)이다. 이 스키마는 Claude/Upstage Solar/OpenAI/네이버 하이퍼클로바X 모두 공식 지원하는 구조화 출력(JSON mode/tool use) 형태로 짰기 때문에 벤더가 바뀌어도 `calc/`, `proposal/` 쪽은 안 건드려도 된다.
- `llm/extractor.py`는 지금 규칙 기반 더미 파서다. 깔끔한 문장(`"무화과 40kg 오늘 낼게요 9000원에"`)은 잘 뽑지만, 사투리/구어체(`"무화과 마흔 상자 오늘 낼란디"`)는 숫자를 한글로 말하면 못 잡는다 — 이게 실제 LLM이 꼭 필요한 지점이다. 더미 파서는 확신 없는 필드를 추측해서 채우지 않고 `low_confidence_fields`에 명시해서 "되물어 확인" 단계로 넘기도록 설계했다 (틀린 값을 그대로 확정하는 것보다 안전).
- 희망가격(`hope_price`)이 비어 있는 건 "불확실"이 아니라 "AI가 추천가를 제시해야 하는 정상 케이스"로 구분해뒀다.
- 상자/개/단 등 kg 이외 단위 -> kg 환산은 아직 TODO (농가·품목마다 상자 크기가 달라서 하드코딩하면 안 됨). 실제 LLM 연동 시 이 부분도 같이 설계 필요.

### 거래 제안서 모듈 설계 메모

- `proposal/generator.py`의 `generate()`가 `llm.extractor.TradeRequest` + `calc.pricing.PriceEstimate`를 받아 제안서(`TradeProposal`)를 만들고, `format_text()`가 사람이 읽는 텍스트로 변환한다. 필드 구성은 사업 지원서 PDF 샘플 출력(거래번호/일자, 품목/중량, 포장방식, 배송조건, 희망가격, 도매시세, 추천가격범위, 예상수익 등) 기준.
- **포장방식/배송조건은 아직 못 채운다** — 지금 LLM 추출 스키마에 없는 정보라 "(미입력 — 농가 확인 필요)"로 표시하고 disclaimer에 남긴다. 농가가 음성으로 말하게 할지(`llm/schema.py` 확장) 아니면 품목별 기본값을 쓸지 팀에서 정해야 함.
- "오늘 내는 편이 유리합니다" 같은 타이밍 추천 문구는 **의도적으로 넣지 않았다** — 최근 시세 추세 비교 로직이 아직 없어서, 근거 없이 그런 문구를 넣는 건 과장이라고 판단했다. 나중에 시계열 비교가 생기면 추가.
- 제안서에는 항상 "참고사항" 섹션이 붙는다: 음성 인식 확신도 낮은 필드, 계산에 쓰인 PLACEHOLDER 상수 고지, 샘플 수가 적을 때 신뢰도 경고 — 사용자 테스트 전까지 숫자를 과신하지 않도록 하기 위함.

### KAMIS 키 발급 후 해야 할 작업

1. `data/kamis_client.py`의 `USE_DUMMY = False`로 변경
2. `_fetch_real()` 함수 구현 (requests로 실제 엔드포인트 호출, 키는 환경변수로 주입 — 코드에 하드코딩 금지)
3. 실제 응답 필드가 `PriceRecord`와 다르면 두 곳 다 맞춰서 수정
4. 5개 품목(무화과/복숭아/양파/부추/청포도) 실제 커버리지 재확인 — 팀 조사 자료의 숫자(무화과 5건/복숭아 139건)는 API 문서 예시일 가능성이 있어 그대로 신뢰하지 말 것
5. `calc/pricing.py`의 PLACEHOLDER 상수(수수료율, 물류비)를 공식 자료 기준으로 교체

## 팀

한국에너지공과대학교(KENTECH) — 전남AI장터혁신단 (멘토 1명, 학생 8명)
