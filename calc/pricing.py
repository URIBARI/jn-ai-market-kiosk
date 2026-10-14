"""
calc/pricing.py

추천가격 / 예상수익 / 직거래(가락시장 경매 경로 대비) 절감액을 계산하는
규칙 기반(rule-based) 로직. LLM이 계산하는 게 아니라 이 모듈이 결정론적으로
계산한다 — 재현성, 테스트 가능성, 설명 가능성(제안서에 "산출 근거" 표시) 확보를 위함.

** 중요: 아래 PLACEHOLDER 상수는 출처가 확인되지 않은 가정치다. **
실제 가락시장(서울시농수산식품공사 등) 공시 위탁수수료율, 이중 물류비 수준은
팀에서 공식 자료로 반드시 재확인 후 교체해야 한다. 지금 이 숫자로 나온 "절감액"을
보고서/발표자료에 실제 효과인 것처럼 인용하지 말 것 — 파이프라인 검증용이다.
"""

from dataclasses import dataclass
from statistics import mean

# --- PLACEHOLDER 상수 (출처 미확인, 공식 자료로 재검증 전까지는 참고용) ---
AUCTION_COMMISSION_RATE = 0.07                  # 가락시장 위탁경매 수수료율 가정치 (TODO)
AUCTION_DOUBLE_LOGISTICS_COST_PER_KG = 300       # 산지->가락시장->재배송 이중 물류비 가정치 (원/kg, TODO)
DIRECT_TRADE_LOGISTICS_COST_PER_KG = 150          # 직거래 1회 배송 물류비 가정치 (원/kg, TODO)
DIRECT_TRADE_PLATFORM_FEE_RATE = 0.03              # 직거래 플랫폼/중개 수수료 가정치 (TODO)


@dataclass
class PriceEstimate:
    item_nm: str
    sample_size: int
    market_avg_price: float         # 원/kg, 최근 시세 평균
    market_min_price: float
    market_max_price: float
    recommended_price_low: float
    recommended_price_high: float
    expected_revenue: float          # 예상 수취액 (수량 반영)
    auction_route_net_price: float    # 가락시장 경매 경로 예상 수취 단가
    direct_trade_net_price: float      # 직거래 경로 예상 수취 단가
    savings_per_kg: float               # 직거래 - 경매 경로 차액 (원/kg)
    savings_total: float                 # 수량 반영 총 절감액


def _to_per_kg(price_records):
    """단위(unit_qty, unit_nm) 기준으로 kg당 단가 리스트를 만든다.
    TODO: kg 이외 단위(개, 단, 박스 등)가 섞여 들어올 경우의 실제 환산 계수는
    품목별로 다르므로 실데이터 확보 후 보완 필요. 지금은 unit_qty로만 나눈다."""
    per_kg = []
    for r in price_records:
        qty = r.unit_qty if r.unit_qty else 1.0
        per_kg.append(r.scsbd_prc / qty)
    return per_kg


def estimate(item_nm, price_records, target_qty_kg):
    """
    item_nm: 품목명
    price_records: data.kamis_client.PriceRecord 리스트 (동일 품목, 최근 기간 데이터)
    target_qty_kg: 농가가 출하하려는 수량 (kg)
    """
    if not price_records:
        raise ValueError(f"{item_nm}: 참고할 시세 데이터가 없습니다 (기간/품목 확인 필요)")
    if target_qty_kg <= 0:
        raise ValueError("target_qty_kg는 0보다 커야 합니다")

    per_kg_prices = _to_per_kg(price_records)
    avg = mean(per_kg_prices)
    lo, hi = min(per_kg_prices), max(per_kg_prices)

    # 추천가격 범위: 최근 평균 ± 10% (가장 단순한 규칙. 추후 최근일 가중평균,
    # 표준편차 기반 구간 등으로 고도화 가능 — 지금은 뼈대만)
    rec_low = round(avg * 0.9, -1)
    rec_high = round(avg * 1.1, -1)
    rec_mid = (rec_low + rec_high) / 2

    expected_revenue = rec_mid * target_qty_kg

    # 경매 경로: 낙찰가 평균에서 수수료 차감, 이중 물류비는 농가 부담으로 가정
    auction_net = avg * (1 - AUCTION_COMMISSION_RATE) - AUCTION_DOUBLE_LOGISTICS_COST_PER_KG

    # 직거래 경로: 추천가(중간값)에서 플랫폼 수수료 + 단일 물류비 차감
    direct_net = rec_mid * (1 - DIRECT_TRADE_PLATFORM_FEE_RATE) - DIRECT_TRADE_LOGISTICS_COST_PER_KG

    savings_per_kg = direct_net - auction_net
    savings_total = savings_per_kg * target_qty_kg

    return PriceEstimate(
        item_nm=item_nm,
        sample_size=len(price_records),
        market_avg_price=round(avg, 1),
        market_min_price=round(lo, 1),
        market_max_price=round(hi, 1),
        recommended_price_low=rec_low,
        recommended_price_high=rec_high,
        expected_revenue=round(expected_revenue, 0),
        auction_route_net_price=round(auction_net, 1),
        direct_trade_net_price=round(direct_net, 1),
        savings_per_kg=round(savings_per_kg, 1),
        savings_total=round(savings_total, 0),
    )
