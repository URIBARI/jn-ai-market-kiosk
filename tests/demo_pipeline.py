"""
STT/LLM 없이 data -> calc 파이프라인만 더미 데이터로 끝까지 돌려보는 수동 데모.
실행: python3 tests/demo_pipeline.py
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.kamis_client import get_prices, TARGET_ITEMS  # noqa: E402
from calc.pricing import estimate  # noqa: E402


def main():
    end = date.today()
    start = end - timedelta(days=13)

    print(f"조회 기간: {start} ~ {end} (더미 데이터 — 실제 시세 아님)\n")
    for item in TARGET_ITEMS:
        records = get_prices(item, start, end)
        if not records:
            records = get_prices(item, end - timedelta(days=59), end)
        if not records:
            print(f"[{item}] 더미 데이터 없음 (기간을 더 넓혀야 함)")
            continue
        r = estimate(item, records, target_qty_kg=80)
        print(
            f"[{item}] 샘플 {r.sample_size}건 | 평균 {r.market_avg_price}원/kg "
            f"({r.market_min_price}~{r.market_max_price}) | "
            f"추천가 {r.recommended_price_low}~{r.recommended_price_high}원/kg | "
            f"예상수익(80kg) {r.expected_revenue:,.0f}원 | "
            f"직거래 절감(kg당) {r.savings_per_kg:+.1f}원"
        )


if __name__ == "__main__":
    main()
