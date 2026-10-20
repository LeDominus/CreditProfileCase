"""Тесты аннуитетного калькулятора (src/core/calc_payment.py)."""

import pytest

from src.core.calc_payment import calculate_annuity_payment


class TestCalculateAnnuityPayment:
    def test_known_example(self):
        # 1 000 000 ₽, 18% годовых, 12 месяцев -> аннуитет ~91 680 ₽/мес
        payment = calculate_annuity_payment(1_000_000, 18.0, 12)
        assert payment == pytest.approx(91_680.0, rel=1e-3)

    def test_long_term_payment(self):
        # 5 000 000 ₽, 16.5%, 60 месяцев -> платёж меньше суммы/60 с процентами
        payment = calculate_annuity_payment(5_000_000, 16.5, 60)
        assert 100_000 < payment < 150_000

    def test_total_exceeds_principal(self):
        monthly = calculate_annuity_payment(1_500_000, 18.9, 24)
        assert monthly * 24 > 1_500_000  # переплата есть

    @pytest.mark.parametrize(
        "credit_sum,annual_rate,months",
        [
            (0, 18.0, 12),
            (-100, 18.0, 12),
            (100_000, 0, 12),
            (100_000, -5.0, 12),
            (100_000, 18.0, 0),
            (100_000, 18.0, -3),
        ],
    )
    def test_invalid_arguments_raise(self, credit_sum, annual_rate, months):
        with pytest.raises(ValueError):
            calculate_annuity_payment(credit_sum, annual_rate, months)
