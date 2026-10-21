"""Юнит-тесты подбора альтернативных продуктов при отказе (п. 2.7 плана MVP)."""

import pytest

from src.config.products import PRODUCTS
from src.core.alternatives import suggest_alternative_products
from src.core.calc_payment import calculate_annuity_payment


def make_profile(**overrides):
    fields = dict(
        funding_purpose="Развитие бизнеса",
        requested_amount=1_500_000,
        business_age_months=36,
        preferred_term_months=24,
        max_monthly_payment=None,
    )
    fields.update(overrides)
    return fields


def product_by_id(product_id):
    return next(p for p in PRODUCTS if p["id"] == product_id)


class TestSuggestAlternatives:
    def test_excludes_requested_product(self):
        alternatives = suggest_alternative_products(make_profile(), exclude_product_id=1)
        assert alternatives
        assert all(alt["id"] != 1 for alt in alternatives)

    def test_limit(self):
        assert len(suggest_alternative_products(make_profile(), exclude_product_id=1)) <= 2
        assert (
            len(suggest_alternative_products(make_profile(), exclude_product_id=1, limit=1))
            == 1
        )

    def test_amount_clamped_to_product_range(self):
        # запрошено 14 млн: «Бизнес-рост» (до 15 млн) исключён — остальным сумма велика
        alternatives = suggest_alternative_products(
            make_profile(requested_amount=14_000_000, preferred_term_months=60),
            exclude_product_id=2,
        )
        assert alternatives
        for alt in alternatives:
            product = product_by_id(alt["id"])
            assert product["min_amount"] <= alt["amount"] <= product["max_amount"]
            assert alt["amount_reduced"] is True

    def test_term_clamped_to_product_range(self):
        alternatives = suggest_alternative_products(
            make_profile(preferred_term_months=60), exclude_product_id=1
        )
        assert alternatives
        for alt in alternatives:
            product = product_by_id(alt["id"])
            assert product["min_term"] <= alt["term_months"] <= product["max_term"]

    def test_skips_products_above_business_age(self):
        # бизнес 4 месяца: «Экспресс» (min_age 3) исключён, остальные (6/12) — не по возрасту
        alternatives = suggest_alternative_products(
            make_profile(business_age_months=4), exclude_product_id=4
        )
        assert alternatives == []

    def test_payments_consistent_with_annuity(self):
        alternatives = suggest_alternative_products(make_profile(), exclude_product_id=1)
        for alt in alternatives:
            monthly = calculate_annuity_payment(
                alt["amount"], float(alt["rate"]), alt["term_months"]
            )
            assert alt["monthly_payment"] == pytest.approx(monthly)
            assert alt["total_repayment"] == pytest.approx(monthly * alt["term_months"])
            assert alt["overpayment"] == pytest.approx(
                alt["total_repayment"] - alt["amount"]
            )

    def test_affordable_respects_max_payment(self):
        alternatives = suggest_alternative_products(
            make_profile(max_monthly_payment=10_000), exclude_product_id=1
        )
        assert alternatives
        assert all(alt["affordable"] is False for alt in alternatives)

    def test_purpose_match_prefers_relevant_product(self):
        # цель «Покупка оборудования»: «Экспресс» (любые цели) должен опережать нерелевантные
        alternatives = suggest_alternative_products(
            make_profile(funding_purpose="Покупка оборудования"), exclude_product_id=3
        )
        assert alternatives
        assert alternatives[0]["purpose_match"] is True

    def test_no_amount_or_term_no_alternatives(self):
        assert suggest_alternative_products({"business_age_months": 36}) == []