"""
더미 데이터 기준으로 data -> calc 파이프라인이 깨지지 않는지 확인하는 테스트.
실행: python3 -m unittest discover -s tests (또는 python3 tests/test_calc.py)

표준 라이브러리 unittest만 사용 — pytest 미설치 환경에서도 바로 돈다.
"""

import os
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.kamis_client import get_prices, TARGET_ITEMS  # noqa: E402
from calc.pricing import estimate  # noqa: E402


def _records_with_fallback(item, end):
    """더미는 랜덤이라 짧은 기간엔 0건일 수 있어 기간을 늘려 재시도."""
    records = get_prices(item, end - timedelta(days=13), end)
    if not records:
        records = get_prices(item, end - timedelta(days=59), end)
    return records


class TestPricingPipeline(unittest.TestCase):
    def test_all_target_items_produce_estimate(self):
        end = date(2026, 8, 31)
        for item in TARGET_ITEMS:
            records = _records_with_fallback(item, end)
            self.assertTrue(records, f"{item}: 더미 데이터가 0건입니다")
            result = estimate(item, records, target_qty_kg=80)
            self.assertGreater(result.market_avg_price, 0)
            self.assertLessEqual(result.recommended_price_low, result.recommended_price_high)
            self.assertGreater(result.expected_revenue, 0)

    def test_origin_filter_is_applied_locally(self):
        end = date(2026, 8, 31)
        all_records = get_prices("무화과", end - timedelta(days=59), end)
        filtered = get_prices("무화과", end - timedelta(days=59), end, origin_filter="영암")
        self.assertTrue(all(r.plor_nm.find("영암") != -1 for r in filtered))
        self.assertLessEqual(len(filtered), len(all_records))

    def test_savings_calculation_runs(self):
        end = date(2026, 8, 31)
        records = _records_with_fallback("무화과", end)
        result = estimate("무화과", records, target_qty_kg=80)
        # PLACEHOLDER 상수에 따라 부호가 달라질 수 있어 값 자체는 검증하지 않고
        # 계산이 정상적으로 수행되는지만 확인한다 (상수 검증은 별도 작업).
        self.assertIsInstance(result.savings_per_kg, float)
        self.assertIsInstance(result.savings_total, float)

    def test_invalid_item_raises(self):
        with self.assertRaises(ValueError):
            get_prices("사과", date(2026, 8, 1), date(2026, 8, 2))

    def test_empty_records_raises(self):
        with self.assertRaises(ValueError):
            estimate("무화과", [], target_qty_kg=80)


if __name__ == "__main__":
    unittest.main()
