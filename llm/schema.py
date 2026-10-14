"""
llm/schema.py

STT 텍스트 -> LLM 정보 구조화 단계의 출력 계약(contract).
calc/pricing.py가 기대하는 입력(품목, 수량(kg), 희망가격, 출하일)과
1:1로 맞물리도록 설계했다 — 이 스키마가 바로 STT/LLM/calc 세 모듈 사이의 경계다.

TRADE_REQUEST_JSON_SCHEMA는 실제 LLM API의 구조화 출력(JSON mode / tool use /
function calling) 기능에 그대로 넘길 수 있는 JSON Schema 형태로 작성했다.
후보로 비교했던 Claude(Anthropic) / Upstage Solar / OpenAI / 네이버 하이퍼클로바X
모두 이런 형태의 스키마 기반 구조화 출력을 공식 지원한다(STT/LLM 비교 자료 기준).
"""

TARGET_ITEMS = ["무화과", "복숭아", "양파", "부추", "청포도"]

# 농가가 실제로 입에 올릴 법한 수량 단위. kg 환산 계수는 전부 TODO —
# 상자 크기는 품목·농가마다 달라서 하드코딩하면 안 되고, 음성으로 다시
# 확인하거나(되물어 확인) 농가별 설정값으로 관리해야 한다.
KNOWN_QTY_UNITS = ["kg", "킬로", "상자", "박스", "개", "단", "접"]

TRADE_REQUEST_JSON_SCHEMA = {
    "name": "trade_request",
    "description": "농가의 음성 발화에서 추출한 거래 요청 정보",
    "schema": {
        "type": "object",
        "properties": {
            "item_nm": {
                "type": "string",
                "enum": TARGET_ITEMS,
                "description": "품목명. 반드시 5개 타깃 품목 중 하나로 정규화할 것 "
                                "(예: '무화가' -> '무화과').",
            },
            "qty_value": {
                "type": "number",
                "description": "수량 (숫자만, 단위는 qty_unit에 별도 기재)",
            },
            "qty_unit": {
                "type": "string",
                "description": "수량 단위 (kg, 상자, 개 등). 모르면 null.",
            },
            "hope_price": {
                "type": ["number", "null"],
                "description": "농가가 말한 희망 단가(원). 언급 안 했으면 null "
                                "-- 이 경우 AI가 추천가를 제시해야 함.",
            },
            "hope_price_unit": {
                "type": ["string", "null"],
                "description": "희망가격의 단위 (원/kg 등). hope_price가 null이면 같이 null.",
            },
            "ship_date": {
                "type": ["string", "null"],
                "description": "출하 희망일 (YYYY-MM-DD). '오늘', '내일' 같은 상대 표현은 "
                                "발화 시점 기준으로 절대 날짜로 변환해서 채울 것.",
            },
            "low_confidence_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "추출 확신이 낮은 필드명 목록. 사투리/생략 등으로 "
                                "불확실하면 여기 채워서 '되물어 확인' 단계에서 "
                                "농가에게 재확인하도록 한다.",
            },
        },
        "required": ["item_nm", "qty_value", "qty_unit", "low_confidence_fields"],
    },
}
