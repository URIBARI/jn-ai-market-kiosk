"""
data/kamis_client.py

KAMIS(농산물유통정보) 연동 모듈.

현재는 KAMIS Open API 키 발급 대기 중이라 더미(dummy) 모드로만 동작한다.
실제 키가 발급되면 USE_DUMMY = False 로 바꾸고 _fetch_real()만 구현하면 되며,
다른 모듈(calc/, llm/, proposal/)은 전혀 수정할 필요가 없도록 설계했다.

응답 필드 스키마는 팀 조사 자료(CES 조사내용 PDF, "데이터 API" 슬라이드)에서 확인한
구조를 따른다. 단, 그 슬라이드의 JSON 예시는 지명이 "전남광주통합특별시"처럼
실제 행정구역명과 맞지 않는 부분이 있어 "API 문서의 샘플 응답"일 가능성이 있다.
즉 무화과 5건/복숭아 139건이라는 숫자를 "실제 라이브 데이터로 확인됨"이라고
단정하면 안 되고, 실제 키 수령 후 반드시 재검증해야 한다.

※ 조사 자료 기준으로 알려진 API 제약 (실제 키로 재검증 필요):
  1. 등급(grade) 필드 없음 -> 등급별 단가 분석 불가, 별도 데이터로 보완 필요
  2. 원산지 조건검색(cond) 불가 -> 전건 수신 후 로컬 필터링 필요 (호출량 증가)
  3. 일자 단위로만 조회 가능 -> 기간 조회 시 날짜 루프 필요
  (이 모듈은 위 세 가지 제약을 이미 반영한 구조로 짜여 있음: get_prices()가
   날짜 루프를 돌고, origin_filter는 로컬에서 필터링한다.)
"""

from dataclasses import dataclass
from datetime import date, timedelta
import random

TARGET_ITEMS = ["무화과", "복숭아", "양파", "부추", "청포도"]

# KAMIS 키 발급되면 False로 전환. 그 전까지는 전부 더미 데이터로 동작.
USE_DUMMY = True


@dataclass
class PriceRecord:
    item_nm: str       # corp_gds_item_nm: 품목명
    vrty_nm: str        # corp_gds_vrty_nm: 품종명
    whsl_mrkt_nm: str    # whsl_mrkt_nm: 도매시장명
    plor_nm: str          # plor_nm: 산지명
    scsbd_dt: str           # scsbd_dt: 낙찰일시
    scsbd_prc: float         # scsbd_prc: 낙찰가(단가)
    unit_nm: str               # unit_nm: 단위 (kg 등)
    unit_qty: float              # unit_qty: 단위물량
    qty: float                     # qty: 수량
    trd_se: str                      # trd_se: 거래구분 (경매 등)


def get_prices(item_nm, start_date, end_date, origin_filter=None):
    """
    item_nm: 품목명 (TARGET_ITEMS 중 하나)
    start_date, end_date: date 객체. API가 일자 단위 조회만 지원한다고 가정하고
                           내부적으로 날짜 루프를 돈다 (제약 3).
    origin_filter: 산지명 부분일치 필터. API가 원산지 조건검색을 지원하지 않는다고
                   가정하고 전건을 받아온 뒤 로컬에서 필터링한다 (제약 2).
    """
    if item_nm not in TARGET_ITEMS:
        raise ValueError(f"대상 품목이 아닙니다: {item_nm}")
    if start_date > end_date:
        raise ValueError("start_date가 end_date보다 늦습니다")

    records = []
    d = start_date
    while d <= end_date:
        if USE_DUMMY:
            records.extend(_fetch_dummy(item_nm, d))
        else:
            records.extend(_fetch_real(item_nm, d))
        d += timedelta(days=1)

    if origin_filter:
        records = [r for r in records if origin_filter in r.plor_nm]

    return records


def _fetch_dummy(item_nm, d):
    """날짜별 더미 레코드 생성.

    주의: 여기 숫자는 '파이프라인이 끝까지 도는지' 검증용 가짜 값이다.
    실제 시세 수준이나 계절성 패턴을 반영한 게 아니므로, 이 값을 보고서나
    발표자료에 실제 시세인 것처럼 인용하면 안 된다.
    """
    base_price = {
        "무화과": 9000,
        "복숭아": 6000,
        "양파": 1200,
        "부추": 3500,
        "청포도": 11000,
    }[item_nm]

    # 아주 단순한 계절 가중치 (7월을 성수기로 가정) -- 실제 패턴 아님, 참고용
    month = d.month
    seasonal = 1.0 + 0.3 * (0.5 - abs(((month - 7) % 12) / 12 - 0.5))

    rng = random.Random(f"{item_nm}-{d.isoformat()}")
    n = rng.randint(0, 4)  # 하루 0~4건 (랜덤이라 운이 나쁘면 특정 기간에 0건일 수 있음)

    markets = ["광주각화", "춘천", "영등포가락", "서울강서"]
    origins = ["전남 영암군", "전남 나주시", "전남 해남군", "강원 춘천시"]

    records = []
    for _ in range(n):
        price = round(base_price * seasonal * rng.uniform(0.85, 1.15), -2)
        records.append(PriceRecord(
            item_nm=item_nm,
            vrty_nm=f"{item_nm}(일반)",
            whsl_mrkt_nm=rng.choice(markets),
            plor_nm=rng.choice(origins),
            scsbd_dt=d.isoformat(),
            scsbd_prc=price,
            unit_nm="kg",
            unit_qty=1.0,
            qty=rng.randint(10, 150),
            trd_se="경매",
        ))
    return records


def _fetch_real(item_nm, d):
    """TODO: KAMIS API 키 발급 후 구현.

    1) requests로 실제 엔드포인트 호출 (키는 환경변수 KAMIS_API_KEY 등으로 주입,
       절대 코드에 하드코딩/커밋하지 말 것 -- .gitignore에 .env, *.key 이미 포함돼 있음)
    2) 응답 JSON -> PriceRecord 리스트로 파싱
    3) 실제 필드명이 조사 자료의 예시와 다르면 이 함수와 PriceRecord 둘 다 맞춰서 수정

    이 함수 하나만 구현하면 get_prices()를 호출하는 calc/, llm/, proposal/ 쪽은
    전혀 수정할 필요가 없다.
    """
    raise NotImplementedError("KAMIS 실제 API 연동 미구현 — API 키 발급 후 작성 예정")
