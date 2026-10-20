"""Юнит-тесты скоринговой модели (линейное уравнение с весами)."""

import pytest

from src.config.scoring_config import (
    APPROVE_SCORE,
    CONDITIONS_SCORE,
    SCORING_BASE,
    TARGET_BURDEN_RATIO,
)
from src.core.scoring import (
    DECISION_APPROVED,
    DECISION_APPROVED_WITH_CHANGES,
    DECISION_NEEDS_INFO,
    DECISION_REJECTED,
    score_application,
)

PRODUCT = {
    "id": 1,
    "name": "Оборотный капитал",
    "rate": 18.9,
    "min_amount": 300_000,
    "max_amount": 5_000_000,
    "min_term": 6,
    "max_term": 36,
    "min_age": 6,
}

AMOUNT = 1_500_000
TERM = 24


def make_profile(**overrides):
    profile = {
        "business_age_months": 36,
        "monthly_revenue": 800_000,
        "monthly_profit": 150_000,
        "requested_amount": AMOUNT,
        "preferred_term_months": TERM,
    }
    profile.update(overrides)
    return profile


class TestDecisions:
    def test_strong_profile_approved(self):
        result = score_application(make_profile(), PRODUCT, AMOUNT, TERM)
        assert result.decision == DECISION_APPROVED
        assert result.score >= APPROVE_SCORE
        assert len(result.factors) == 4
        assert result.explanation

    def test_weak_profile_rejected(self):
        result = score_application(
            make_profile(monthly_revenue=200_000, monthly_profit=10_000, business_age_months=6),
            PRODUCT,
            AMOUNT,
            TERM,
        )
        assert result.decision == DECISION_REJECTED
        assert result.score < CONDITIONS_SCORE
        assert result.score >= 0

    def test_medium_profile_approved_with_changes(self):
        # платёж ~25% выручки: выше целевой нагрузки, но ниже порога отказа
        result = score_application(
            make_profile(monthly_revenue=300_000, monthly_profit=45_000, business_age_months=30),
            PRODUCT,
            AMOUNT,
            TERM,
        )
        assert result.decision == DECISION_APPROVED_WITH_CHANGES
        assert CONDITIONS_SCORE <= result.score < APPROVE_SCORE
        assert result.suggested_amount is not None
        assert result.suggested_amount < AMOUNT
        assert result.suggested_term_months == TERM
        # предложенный платёж укладывается в целевую нагрузку
        assert result.suggested_monthly_payment / 300_000 <= TARGET_BURDEN_RATIO + 1e-6

    def test_term_extension_suggestion(self):
        # нагрузка в норме, но балл ниже одобрения: предлагаем максимальный срок
        result = score_application(
            make_profile(monthly_revenue=350_000, monthly_profit=50_000, business_age_months=20),
            PRODUCT,
            AMOUNT,
            TERM,
        )
        assert result.decision == DECISION_APPROVED_WITH_CHANGES
        assert result.suggested_term_months == PRODUCT["max_term"]
        assert result.suggested_amount == AMOUNT
        assert result.suggested_monthly_payment < AMOUNT  # платёж меньше — тривиально, но проверяем наличие

    def test_missing_fields_needs_info(self):
        result = score_application(
            make_profile(monthly_revenue=None, monthly_profit=None),
            PRODUCT,
            AMOUNT,
            TERM,
        )
        assert result.decision == DECISION_NEEDS_INFO
        assert result.score is None
        assert set(result.missing_fields) == {"monthly_revenue", "monthly_profit"}
        assert result.factors == []


class TestModelProperties:
    def test_score_is_base_plus_contributions(self):
        result = score_application(make_profile(), PRODUCT, AMOUNT, TERM)
        expected = SCORING_BASE + sum(f["contribution"] for f in result.factors)
        assert result.score == pytest.approx(min(max(expected, 0.0), 100.0), abs=1e-6)

    def test_deterministic(self):
        first = score_application(make_profile(), PRODUCT, AMOUNT, TERM)
        second = score_application(make_profile(), PRODUCT, AMOUNT, TERM)
        assert first.to_dict() == second.to_dict()

    def test_factors_have_weights_and_labels(self):
        result = score_application(make_profile(), PRODUCT, AMOUNT, TERM)
        for factor in result.factors:
            assert factor["weight"] > 0
            assert factor["label"]
            assert -1.0 <= factor["normalized"] <= 1.0

    def test_monthly_payment_computed_when_not_provided(self):
        result = score_application(make_profile(), PRODUCT, AMOUNT, TERM)
        # платёж должен совпадать с аннуитетом по продукту
        from src.core.calc_payment import calculate_annuity_payment

        expected = calculate_annuity_payment(AMOUNT, PRODUCT["rate"], TERM)
        burden = next(f for f in result.factors if f["name"] == "payment_burden")
        assert burden["value"].startswith(f"{expected / 800_000 * 100:.1f}%")