"""
proposal/generator.py

llm.extractor.TradeRequest + calc.pricing.PriceEstimate -> 거래 제안서(TradeProposal).

제안서 필드 구성은 사업 지원서 PDF의 샘플 출력(거래번호/일자, 품목/중량, 포장방식,
배송조건, 희망가격, 도매시세, 예상물류비, 예상수수료, 추천가격범위, 예상수익)을
기준으로 맞췄다.

** 현재 못 채우는 필드 (TODO, 추측해서 채우지 않음) **
- packaging(포장방식), delivery_condition(배송조건): 지금 LLM 추출 스키마에
  없는 정보다. 농가가 음성으로 말하게 할지(llm/schema.py 확장), 아니면
  품목별 기본값으로 둘지 팀 논의 필요. 지금은 "(미입력)"으로 채우고
  disclaimers에 명시한다 — 빈 값을 그럴듯한 기본값으로 지어내지 않는다.
- "오늘 내는 편이 유리합니다" 류의 타이밍 추천: 최근 시세 추세를 비교하는
  로직이 아직 없어서 넣지 않았다. 구현 없이 문구만 넣으면 근거 없는 주장이 되므로
  의도적으로 뺐다 (추후 시계열 비교 로직 추가되면 넣을 것).
"""

import random
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TradeProposal:
    proposal_no: str
    created_at: str  # ISO timestamp
    item_nm: str
    qty_value: float
    qty_unit: str
    packaging: str
    delivery_condition: str
    hope_price: float | None
    hope_price_unit: str | None
    market_avg_price: float
    recommended_price_low: float
    recommended_price_high: float
    expected_revenue: float
    auction_route_net_price: float
    direct_trade_net_price: float
    savings_per_kg: float
    savings_total: float
    disclaimers: list = field(default_factory=list)


def generate(trade_request, price_estimate):
    """
    trade_request: llm.extractor.TradeRequest
    price_estimate: calc.pricing.PriceEstimate (trade_request.item_nm과 동일 품목 기준)
    """
    if trade_request.item_nm != price_estimate.item_nm:
        raise ValueError(
            f"품목 불일치: trade_request={trade_request.item_nm}, "
            f"price_estimate={price_estimate.item_nm}"
        )

    disclaimers = []

    if trade_request.low_confidence_fields:
        disclaimers.append(
            "다음 항목은 음성 인식 확신도가 낮아 재확인이 필요합니다: "
            + ", ".join(trade_request.low_confidence_fields)
        )

    packaging = "(미입력 — 농가 확인 필요)"
    delivery_condition = "(미입력 — 농가 확인 필요)"
    disclaimers.append(
        "포장방식/배송조건은 아직 음성 입력으로 받지 않습니다 (llm/schema.py 확장 필요)."
    )

    disclaimers.append(
        "추천가격·절감액 계산에 쓰인 수수료율/물류비 상수는 PLACEHOLDER입니다 "
        "(calc/pricing.py 주석 참고, 공식 자료로 검증 전까지 참고용)."
    )

    if price_estimate.sample_size < 5:
        disclaimers.append(
            f"참고한 시세 데이터가 {price_estimate.sample_size}건으로 적어 "
            "추천가격의 신뢰도가 낮을 수 있습니다."
        )

    proposal_no = (
        f"{datetime.now():%Y%m%d}-{trade_request.item_nm}-{random.randint(1000, 9999)}"
    )

    return TradeProposal(
        proposal_no=proposal_no,
        created_at=datetime.now().isoformat(timespec="seconds"),
        item_nm=trade_request.item_nm,
        qty_value=trade_request.qty_value,
        qty_unit=trade_request.qty_unit,
        packaging=packaging,
        delivery_condition=delivery_condition,
        hope_price=trade_request.hope_price,
        hope_price_unit=trade_request.hope_price_unit,
        market_avg_price=price_estimate.market_avg_price,
        recommended_price_low=price_estimate.recommended_price_low,
        recommended_price_high=price_estimate.recommended_price_high,
        expected_revenue=price_estimate.expected_revenue,
        auction_route_net_price=price_estimate.auction_route_net_price,
        direct_trade_net_price=price_estimate.direct_trade_net_price,
        savings_per_kg=price_estimate.savings_per_kg,
        savings_total=price_estimate.savings_total,
        disclaimers=disclaimers,
    )


def format_text(p: TradeProposal) -> str:
    """고령 농어업인 대상이므로 큰 글씨/음성 출력을 염두에 두고 짧은 문장,
    쉬운 표현 위주로 구성. 키오스크 화면/음성 출력 양쪽에 재사용 가능하도록
    순수 텍스트로 만든다 (레이아웃은 UI 쪽에서 별도 처리)."""
    lines = [
        "===== 거래 제안서 =====",
        f"제안번호: {p.proposal_no}",
        f"작성일시: {p.created_at}",
        "",
        f"품목: {p.item_nm}",
        f"수량: {p.qty_value:g}{p.qty_unit}",
        f"포장방식: {p.packaging}",
        f"배송조건: {p.delivery_condition}",
        "",
    ]

    if p.hope_price is not None:
        lines.append(f"희망가격: {p.hope_price_unit} {p.hope_price:,.0f}원")
    else:
        lines.append("희망가격: 말씀 안 하셨어요 (아래 추천가격 참고)")

    lines += [
        f"최근 도매시세 평균: {p.market_avg_price:,.0f}원/kg",
        f"추천가격 범위: {p.recommended_price_low:,.0f} ~ {p.recommended_price_high:,.0f}원/kg",
        f"예상 수취액(수량 기준): {p.expected_revenue:,.0f}원",
        "",
        "--- 직거래 vs 가락시장 경매 경로 비교 (참고용) ---",
        f"경매 경로 예상 단가: {p.auction_route_net_price:,.0f}원/kg",
        f"직거래 경로 예상 단가: {p.direct_trade_net_price:,.0f}원/kg",
        f"kg당 절감액: {p.savings_per_kg:+,.0f}원",
        f"총 절감액(수량 기준): {p.savings_total:+,.0f}원",
    ]

    if p.disclaimers:
        lines.append("")
        lines.append("--- 참고사항 ---")
        for d in p.disclaimers:
            lines.append(f"- {d}")

    return "\n".join(lines)
