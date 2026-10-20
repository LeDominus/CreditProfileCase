"""Тесты движка рекомендаций (src/core/recommendations.py)."""

import pytest

from src.core.calc_payment import calculate_annuity_payment
from src.core.recommendations import recommend_products

BASE_PROFILE = {
    "funding_purpose": "Пополнение оборотных средств",
    "requested_amount": 1_500_000,
    "preferred_term_months": 24,
    "business_age_months": 24,
}


class TestFiltering:
    def test_filtered_by_amount(self):
        # 200 000 подходит только «Экспрессу» (100k–1.5M)
        recs = recommend_products({**BASE_PROFILE, "requested_amount": 200_000})
        assert [rec["id"] for rec in recs] == [4]

    def test_filtered_by_term(self):
        # 1.5 млн на 48 месяцев: «Бизнес-рост» (12–60) и «Оборудование» (12–48)
        recs = recommend_products({**BASE_PROFILE, "preferred_term_months": 48})
        assert sorted(rec["id"] for rec in recs) == [2, 3]
        # при равном совпадении цели первым — меньшая ставка (Оборудование 15.9)
        assert recs[0]["id"] == 3

    def test_filtered_by_business_age(self):
        # бизнес 3 месяца: только «Экспресс» (min_age=3)
        recs = recommend_products({**BASE_PROFILE, "business_age_months": 3})
        assert [rec["id"] for rec in recs] == [4]

    def test_nothing_matches_returns_empty(self):
        recs = recommend_products({**BASE_PROFILE, "requested_amount": 50_000_000})
        assert recs == []


class TestRanking:
    def test_purpose_match_first(self):
        recs = recommend_products(
            {
                **BASE_PROFILE,
                "funding_purpose": "Развитие бизнеса",
                "requested_amount": 5_000_000,
                "preferred_term_months": 36,
            }
        )
        assert recs[0]["id"] == 2  # «Бизнес-рост» совпадает по цели
        assert recs[0]["purpose_match"] is True
        assert all(not rec["purpose_match"] for rec in recs[1:])

    def test_limit(self):
        recs = recommend_products(BASE_PROFILE, limit=1)
        assert len(recs) == 1


class TestCalculation:
    def test_monthly_payment_from_annuity_formula(self):
        recs = recommend_products(BASE_PROFILE)
        rec = next(item for item in recs if item["id"] == 1)
        expected = calculate_annuity_payment(1_500_000, 18.9, 24)
        assert rec["monthly_payment"] == pytest.approx(expected)
        assert rec["total_repayment"] == pytest.approx(expected * 24, rel=1e-3)
        assert rec["overpayment"] == pytest.approx(expected * 24 - 1_500_000, rel=1e-3)

    def test_affordable_flag(self):
        tight = recommend_products({**BASE_PROFILE, "max_monthly_payment": 10_000})
        assert tight and all(not rec["affordable"] for rec in tight)

        comfortable = recommend_products({**BASE_PROFILE, "max_monthly_payment": 100_000})
        assert comfortable and all(rec["affordable"] for rec in comfortable)

    def test_unknown_profile_fields_do_not_filter(self):
        # пустой профиль — фильтры не применяются, возвращён весь каталог (с лимитом)
        recs = recommend_products({})
        assert len(recs) == 3
