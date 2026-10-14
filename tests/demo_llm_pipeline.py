"""
음성 입력(텍스트로 흉내) -> LLM 구조화(더미) -> 되물어 확인 -> data/calc 더미 파이프라인
까지 전부 이어서 보여주는 데모. STT는 아직 없으므로 '이미 STT를 거친 텍스트'라고
가정하고 시작한다.

실행: python3 tests/demo_llm_pipeline.py
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from llm.extractor import extract, build_confirmation_message  # noqa: E402
from data.kamis_client import get_prices  # noqa: E402
from calc.pricing import estimate  # noqa: E402

SAMPLE_UTTERANCES = [
    "무화과 40kg 오늘 낼게요 9000원에 팔고 싶어요",
    "복숭아 30상자 내일 낼게요",
    "무화과 마흔 상자 오늘 낼란디",  # 사투리 -- 더미 파서 한계를 보여주는 케이스
]


def main():
    today = date.today()
    for text in SAMPLE_UTTERANCES:
        print(f"\n[STT 텍스트] \"{text}\"")
        req = extract(text, reference_date=today)
        print(f"[구조화 결과] item={req.item_nm}, qty={req.qty_value}{req.qty_unit or ''}, "
              f"hope_price={req.hope_price}, ship_date={req.ship_date}")
        print("[되물어 확인 메시지]")
        print(build_confirmation_message(req))

        if req.low_confidence_fields:
            print("-> 확인 필요 항목이 있어 계산 단계로 넘어가지 않음 (실제로는 재질문 필요)")
            continue
        if req.item_nm is None or req.qty_unit != "kg":
            print("-> 이 데모는 kg 단위만 계산까지 이어감 (상자->kg 환산은 TODO)")
            continue

        end = today
        start = end - timedelta(days=13)
        records = get_prices(req.item_nm, start, end) or get_prices(
            req.item_nm, end - timedelta(days=59), end
        )
        result = estimate(req.item_nm, records, target_qty_kg=req.qty_value)
        print(f"[계산 결과] 추천가 {result.recommended_price_low}~{result.recommended_price_high}원/kg "
              f"| 예상수익 {result.expected_revenue:,.0f}원")


if __name__ == "__main__":
    main()
