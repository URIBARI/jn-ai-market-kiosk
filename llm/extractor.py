"""
llm/extractor.py

STT 텍스트 -> 구조화된 TradeRequest 추출.

지금은 실제 LLM API를 아직 붙이지 않았으므로(API 벤더 미확정, 예산/키 문제),
규칙 기반(rule-based) 더미 파서로 동작한다. 목적은 두 가지:
  1) STT -> LLM -> calc 파이프라인이 끝까지 돌아가는지 더미로 검증
  2) 실제 LLM 연동 시 입력/출력 계약(schema.py)이 흔들리지 않도록 미리 고정

더미 파서는 "무화과 마흔 상자 오늘 낼란디"처럼 복잡한 사투리/생략은 처리 못 한다.
그런 케이스는 실제 LLM(권장: Claude -- 구조화 출력 안정적, 가격대비 성능 좋음,
STT/LLM 비교 자료 기준)로 교체해야 풀리는 문제이고, 그게 바로 이 모듈에서
LLM이 필요한 이유다. 더미 파서가 처리 못 하는 입력은 예외 없이
low_confidence_fields에 걸리게 만들어서, 실제 LLM으로 바꿨을 때도 같은 방식으로
'자신없는 필드는 되물어 확인'하도록 설계했다.
"""

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from llm.schema import TARGET_ITEMS, KNOWN_QTY_UNITS

USE_DUMMY = True  # 실제 LLM API 연동되면 False로 전환


@dataclass
class TradeRequest:
    raw_text: str
    item_nm: str | None
    qty_value: float | None
    qty_unit: str | None
    hope_price: float | None = None
    hope_price_unit: str | None = None
    ship_date: str | None = None  # YYYY-MM-DD
    low_confidence_fields: list = field(default_factory=list)


_QTY_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(" + "|".join(KNOWN_QTY_UNITS) + r")"
)
_PRICE_PATTERN = re.compile(r"(\d[\d,]*)\s*원")


def extract(text, reference_date=None):
    """text: STT가 변환한 농가 발화 텍스트.
    reference_date: '오늘'/'내일' 같은 상대 날짜를 변환할 기준일 (기본값 오늘)."""
    if reference_date is None:
        reference_date = date.today()

    if USE_DUMMY:
        return _extract_dummy(text, reference_date)
    return _extract_real(text, reference_date)


def _extract_dummy(text, reference_date):
    low_conf = []

    item_nm = next((item for item in TARGET_ITEMS if item in text), None)
    if item_nm is None:
        low_conf.append("item_nm")

    qty_value, qty_unit = None, None
    qty_match = _QTY_PATTERN.search(text)
    if qty_match:
        qty_value = float(qty_match.group(1))
        qty_unit = qty_match.group(2)
    else:
        low_conf.append("qty_value")
        low_conf.append("qty_unit")

    hope_price, hope_price_unit = None, None
    price_match = _PRICE_PATTERN.search(text)
    if price_match:
        hope_price = float(price_match.group(1).replace(",", ""))
        hope_price_unit = f"원/{qty_unit}" if qty_unit else "원"
    # 희망가격은 농가가 말 안 할 수도 있으므로 못 찾아도 low_confidence에 넣지 않음
    # (그건 "모름"이 아니라 "AI가 추천해야 하는 정상 케이스"이기 때문)

    ship_date = None
    if "오늘" in text:
        ship_date = reference_date.isoformat()
    elif "내일" in text:
        ship_date = (reference_date + timedelta(days=1)).isoformat()
    else:
        date_match = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
        if date_match:
            month, day = int(date_match.group(1)), int(date_match.group(2))
            year = reference_date.year
            ship_date = date(year, month, day).isoformat()
        else:
            low_conf.append("ship_date")

    return TradeRequest(
        raw_text=text,
        item_nm=item_nm,
        qty_value=qty_value,
        qty_unit=qty_unit,
        hope_price=hope_price,
        hope_price_unit=hope_price_unit,
        ship_date=ship_date,
        low_confidence_fields=low_conf,
    )


def _extract_real(text, reference_date):
    """TODO: 실제 LLM API 연동.
    schema.TRADE_REQUEST_JSON_SCHEMA를 구조화 출력(JSON mode / tool use)으로
    넘기고, 응답을 TradeRequest로 변환한다. 키는 환경변수로 주입
    (코드에 하드코딩 금지, .env는 .gitignore에 이미 포함됨).
    """
    raise NotImplementedError("실제 LLM 연동 미구현 — 벤더/키 확정 후 작성 예정")


def build_confirmation_message(req: TradeRequest) -> str:
    """'되물어 확인' 단계용 메시지 생성 (조사 자료의 유통 시나리오 07:22 단계 대응).
    사투리를 표준 항목으로 정리해서 큰 글씨/음성으로 한 번 더 확인시키는 용도.
    low_confidence_fields가 있으면 그 항목은 추정값이 아니라 '확인이 필요하다'고
    명시한다 — 틀린 값을 그대로 확정하는 것보다 안전하기 때문."""
    lines = []
    item_part = req.item_nm or "(품목 확인 필요)"
    qty_part = (
        f"{req.qty_value:g}{req.qty_unit}" if req.qty_value is not None else "(수량 확인 필요)"
    )
    lines.append(f"{item_part} {qty_part} 맞으신가요?")

    if req.hope_price is not None:
        lines.append(f"희망가격은 {req.hope_price_unit} {req.hope_price:,.0f}원으로 등록할게요.")
    else:
        lines.append("희망가격을 따로 말씀 안 하셨으니, 시세 기준으로 추천가격을 보여드릴게요.")

    if req.ship_date:
        lines.append(f"출하일은 {req.ship_date}로 등록할게요.")
    else:
        lines.append("출하 날짜를 다시 한 번 말씀해 주시겠어요?")

    if req.low_confidence_fields:
        lines.append(f"[확인 필요 항목: {', '.join(req.low_confidence_fields)}]")

    return "\n".join(lines)
