import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from llm.extractor import extract, build_confirmation_message  # noqa: E402


class TestDummyExtractor(unittest.TestCase):
    def test_clean_sentence_extracts_all_fields(self):
        req = extract("무화과 40kg 오늘 낼게요 9000원에 팔고 싶어요", reference_date=date(2026, 8, 31))
        self.assertEqual(req.item_nm, "무화과")
        self.assertEqual(req.qty_value, 40.0)
        self.assertEqual(req.qty_unit, "kg")
        self.assertEqual(req.hope_price, 9000.0)
        self.assertEqual(req.ship_date, "2026-08-31")
        self.assertEqual(req.low_confidence_fields, [])

    def test_missing_item_flagged_low_confidence(self):
        req = extract("40kg 오늘 낼게요", reference_date=date(2026, 8, 31))
        self.assertIsNone(req.item_nm)
        self.assertIn("item_nm", req.low_confidence_fields)

    def test_missing_price_is_not_low_confidence(self):
        # 희망가격 생략은 '불확실'이 아니라 'AI가 추천가 제시' 정상 케이스
        req = extract("복숭아 30상자 내일 낼게요", reference_date=date(2026, 8, 31))
        self.assertIsNone(req.hope_price)
        self.assertNotIn("hope_price", req.low_confidence_fields)
        self.assertEqual(req.ship_date, "2026-09-01")

    def test_dialect_like_sentence_flags_fields_instead_of_guessing(self):
        # 숫자가 한글(마흔)로 오는 사투리/구어체는 더미 파서가 못 잡는다 -- 이건
        # 실제 LLM이 필요한 지점이라는 걸 보여주는 테스트. 추정값을 지어내지 않고
        # low_confidence로 명시하는지만 확인한다.
        req = extract("무화과 마흔 상자 오늘 낼란디", reference_date=date(2026, 8, 31))
        self.assertEqual(req.item_nm, "무화과")
        self.assertIn("qty_value", req.low_confidence_fields)
        self.assertIn("qty_unit", req.low_confidence_fields)

    def test_confirmation_message_mentions_low_confidence_fields(self):
        req = extract("40kg 오늘 낼게요", reference_date=date(2026, 8, 31))
        msg = build_confirmation_message(req)
        self.assertIn("확인 필요", msg)
        self.assertIn("item_nm", msg)


if __name__ == "__main__":
    unittest.main()
