from src.schemas.scoring_schema import ScoringResult
from src.config.scoring_config import (
    APPROVE_SCORE,
    BURDEN_COMFORT_RATIO,
    BURDEN_CRITICAL_RATIO,
    BUSINESS_AGE_FULL_MONTHS,
    CONDITIONS_SCORE,
    COVERAGE_COMFORT_RATIO,
    COVERAGE_CRITICAL_RATIO,
    MARGIN_FULL_RATIO,
    REQUIRED_PROFILE_FIELDS,
    SCORING_BASE,
    SCORING_WEIGHTS,
    SUGGESTED_AMOUNT_STEP,
    TARGET_BURDEN_RATIO,
    DECISION_APPROVED,
    DECISION_APPROVED_WITH_CHANGES,
    DECISION_NEEDS_INFO,
    DECISION_REJECTED,
    FACTOR_LABELS,
    CLAMP_HIGH,
    CLAMP_LOW
)
from src.core.calc_payment import calculate_annuity_payment
from src.utils import clamp

def _factor(key: str, value: str, normalized: float) -> dict:
    weight = SCORING_WEIGHTS[key]
    return {
        "name": key,
        "label": FACTOR_LABELS[key],
        "value": value,
        "normalized": round(normalized, 4),
        "weight": weight,
        "contribution": round(weight * normalized, 4),
    }

def _floor_to_step(amount: float) -> float:
    return float(int(amount // SUGGESTED_AMOUNT_STEP) * int(SUGGESTED_AMOUNT_STEP))


def _invert_annuity(monthly_payment: float, annual_rate: float, months: int) -> float:
    """Максимальная сумма кредита под заданный платёж (обратный аннуитет)"""
    monthly_rate = annual_rate / 12 / 100
    if monthly_rate <= 0:
        return monthly_payment * months
    return monthly_payment * (1 - (1 + monthly_rate) ** -months) / monthly_rate


def _suggest_conditions(
    product: dict,
    revenue: float,
    requested_amount: float,
    term_months: int,
    burden: float,
    coverage: float,
) -> tuple[float | None, int | None, float | None]:
    """Подбор изменённых условий для решения «одобрение с иными условиями»"""
    rate = float(product["rate"])
    min_amount = float(product["min_amount"])
    max_term = int(product["max_term"])

    if burden > TARGET_BURDEN_RATIO:
        amount = _floor_to_step(
            _invert_annuity(revenue * TARGET_BURDEN_RATIO, rate, term_months)
        )
        if min_amount <= amount < requested_amount:
            return amount, term_months, calculate_annuity_payment(amount, rate, term_months)

    if coverage > COVERAGE_COMFORT_RATIO:
        amount = _floor_to_step(revenue * 12 * COVERAGE_COMFORT_RATIO)
        if min_amount <= amount < requested_amount:
            return amount, term_months, calculate_annuity_payment(amount, rate, term_months)

    if term_months < max_term:
        monthly = calculate_annuity_payment(requested_amount, rate, max_term)
        if monthly / revenue <= TARGET_BURDEN_RATIO:
            return requested_amount, max_term, monthly

    return None, None, None


def score_application(
    profile: dict,
    product: dict,
    requested_amount: float,
    term_months: int,
    monthly_payment: float | None = None,
) -> ScoringResult:
    """Скоринг заявки: профиль бизнеса + продукт + параметры -> решение"""
    missing = [name for name in REQUIRED_PROFILE_FIELDS if profile.get(name) is None]
    if missing:
        return ScoringResult(
            score=None,
            decision=DECISION_NEEDS_INFO,
            missing_fields=missing,
            explanation=(
                "Для скоринга не хватает данных профиля: "
                + ", ".join(missing)
                + ". Уточните информацию о бизнесе и отправьте заявку на скоринг повторно."
            ),
        )

    revenue = float(profile["monthly_revenue"])
    profit = float(profile["monthly_profit"])
    age = int(profile["business_age_months"])

    if monthly_payment is None:
        monthly_payment = calculate_annuity_payment(
            float(requested_amount), float(product["rate"]), int(term_months)
        )
    monthly_payment = float(monthly_payment)

    if revenue > 0:
        burden = monthly_payment / revenue
        margin = profit / revenue
        coverage = float(requested_amount) / (revenue * 12)
    else:
        burden = CLAMP_HIGH
        margin = CLAMP_LOW
        coverage = COVERAGE_CRITICAL_RATIO

    burden_pivot = (BURDEN_COMFORT_RATIO + BURDEN_CRITICAL_RATIO) / 2
    burden_span = (BURDEN_CRITICAL_RATIO - BURDEN_COMFORT_RATIO) / 2
    coverage_pivot = (COVERAGE_COMFORT_RATIO + COVERAGE_CRITICAL_RATIO) / 2
    coverage_span = (COVERAGE_CRITICAL_RATIO - COVERAGE_COMFORT_RATIO) / 2

    factors = [
        _factor("business_age", f"{age} мес", min(age / BUSINESS_AGE_FULL_MONTHS, 1.0)),
        _factor("margin", f"{margin * 100:.1f}%", clamp(margin / MARGIN_FULL_RATIO, CLAMP_LOW, CLAMP_HIGH)),
        _factor("payment_burden", f"{burden * 100:.1f}% выручки", clamp((burden_pivot - burden) / burden_span, CLAMP_LOW, CLAMP_HIGH)),
        _factor("amount_coverage", f"{coverage:.2f} годовой выручки", clamp((coverage_pivot - coverage) / coverage_span, CLAMP_LOW, CLAMP_HIGH)),
    ]

    score = round(clamp(SCORING_BASE + sum(f["contribution"] for f in factors), 0.0, 100.0), 2)

    if score >= APPROVE_SCORE:
        return ScoringResult(
            score=score,
            decision=DECISION_APPROVED,
            factors=factors,
            explanation=(
                f"Балл {score:g} из 100 — не ниже порога одобрения ({APPROVE_SCORE:g}). "
                "Заявка одобрена в рамках скоринговой модели."
            ),
        )

    if score >= CONDITIONS_SCORE:
        amount, term, monthly = _suggest_conditions(
            product, revenue, float(requested_amount), int(term_months), burden, coverage
        )
        if amount is None:
            explanation = (
                f"Балл {score:g} из 100 — ниже порога одобрения, но выше порога отказа. "
                f"Улучшить условия в рамках продукта «{product.get('name', '')}» не удалось: "
                "попробуйте другой продукт или уточните данные о бизнесе."
            )
        elif term != term_months:
            explanation = (
                f"Балл {score:g} из 100 — ниже порога одобрения, но выше порога отказа. "
                f"Предлагаем увеличить срок до {term} мес: платёж снизится до "
                f"≈ {monthly:,.0f} ₽/мес. Подтвердите изменённые условия.".replace(",", " ")
            )
        else:
            explanation = (
                f"Балл {score:g} из 100 — ниже порога одобрения, но выше порога отказа. "
                f"Предлагаем снизить сумму до {amount:,.0f} ₽: платёж составит "
                f"≈ {monthly:,.0f} ₽/мес. Подтвердите изменённые условия.".replace(",", " ")
            )
        return ScoringResult(
            score=score,
            decision=DECISION_APPROVED_WITH_CHANGES,
            factors=factors,
            explanation=explanation,
            suggested_amount=amount,
            suggested_term_months=term,
            suggested_monthly_payment=monthly,
        )

    weakest = sorted(factors, key=lambda f: f["contribution"])[:2]
    reasons = "; ".join(f"{f['label']} ({f['value']})" for f in weakest)
    return ScoringResult(
        score=score,
        decision=DECISION_REJECTED,
        factors=factors,
        explanation=(
            f"Балл {score:g} из 100 — ниже порога отказа ({CONDITIONS_SCORE:g}). "
            f"Основные причины: {reasons}."
        ),
    )