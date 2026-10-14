import os
import sys
import unittest
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from llm.extractor import extract  # noqa: E402
from data.kamis_client import get_prices  # noqa: E402
from calc.pricing import estimate  # noqa: E402
from proposal.generator import generate, format_text  # noqa: E402


def _estimate_for(item, qty, end=date(2026, 8, 31)):
    records = get_prices(item, end - timedelta(days=13), end) or get_prices(
        item, end - timedelta(days=59), end
    )
    return estimate(item, records, target_qty_kg=qty)


class TestProposalGenerator(unittest.TestCase):
    def test_generate_from_clean_request(self):
        req = extract("무화과 40kg 오늘 낼게요 9000원에 팔고 싶어요", reference_date=date(2026, 8, 31))
        price_est = _estimate_for(req.item_nm, req.qty_value)
        proposal = generate(req, price_est)

        self.assertEqual(proposal.item_nm, "무화과")
        self.assertEqual(proposal.qty_value, 40.0)
        self.assertEqual(proposal.hope_price, 9000.0)
        # proposal_no은 '작성 시점'(datetime.now()) 기준이지 reference_date 기준이
        # 아니므로, 오늘 날짜 prefix로 확인한다.
        self.assertTrue(proposal.proposal_no.startswith(f"{datetime.now():%Y%m%d}-무화과-"))
        # 희망가격이 있으니 '희망가격 확인 필요' 류 disclaimer는 없어야 함
        self.assertFalse(any("low_confidence_fields" in d for d in proposal.disclaimers))

    def test_generate_flags_low_confidence_fields(self):
        req = extract("무화과 마흔 상자 오늘 낼란디", reference_date=date(2026, 8, 31))
        # 수량 추출 실패했으니 임의로 채워서 calc까지만 테스트 진행
        req.qty_value = 40.0
        price_est = _estimate_for(req.item_nm, req.qty_value)
        proposal = generate(req, price_est)

        self.assertTrue(any("재확인이 필요" in d for d in proposal.disclaimers))
        self.assertTrue(any("qty_value" in d for d in proposal.disclaimers))

    def test_item_mismatch_raises(self):
        req = extract("복숭아 30kg 오늘 낼게요", reference_date=date(2026, 8, 31))
        wrong_est = _estimate_for("무화과", 30.0)
        with self.assertRaises(ValueError):
            generate(req, wrong_est)

    def test_format_text_contains_key_fields(self):
        req = extract("청포도 20kg 내일 낼게요", reference_date=date(2026, 8, 31))
        price_est = _estimate_for(req.item_nm, req.qty_value)
        proposal = generate(req, price_est)
        text = format_text(proposal)

        self.assertIn("거래 제안서", text)
        self.assertIn("청포도", text)
        self.assertIn("추천가격 범위", text)
        self.assertIn("절감액", text)
        self.assertIn("참고사항", text)  # placeholder 상수 고지가 항상 포함돼야 함


if __name__ == "__main__":
    unittest.main()
