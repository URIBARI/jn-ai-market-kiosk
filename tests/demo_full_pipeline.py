"""
(텍스트)STT -> LLM 구조화 -> 되물어 확인 -> data/calc -> 거래 제안서까지
전체 더미 파이프라인을 끝까지 돌려보는 데모.

실행: python3 tests/demo_full_pipeline.py
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from llm.extractor import extract, build_confirmation_message  # noqa: E402
from data.kamis_client import get_prices  # noqa: E402
from calc.pricing import estimate  # noqa: E402
from proposal.generator import generate, format_text  # noqa: E402

SAMPLE_UTTERANCE = "무화과 40kg 오늘 낼게요 9000원에 팔고 싶어요"


def main():
    today = date.today()

    print(f"[STT 텍스트] \"{SAMPLE_UTTERANCE}\"")
    req = extract(SAMPLE_UTTERANCE, reference_date=today)
    print("\n[되물어 확인 메시지]")
    print(build_confirmation_message(req))

    if req.low_confidence_fields or req.item_nm is None:
        print("\n-> 확인 필요 항목이 있어 중단 (실제로는 재질문 후 재시도)")
        return

    end = today
    start = end - timedelta(days=13)
    records = get_prices(req.item_nm, start, end) or get_prices(
        req.item_nm, end - timedelta(days=59), end
    )
    price_est = estimate(req.item_nm, records, target_qty_kg=req.qty_value)

    proposal = generate(req, price_est)
    print("\n" + format_text(proposal))


if __name__ == "__main__":
    main()
