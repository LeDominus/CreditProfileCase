"""Конфигурация скоринговой модели.

Модель — формальная (не ML): линейное уравнение с весами

    score = SCORING_BASE + Σ (weight_i × normalize_i)

Каждый фактор нормируется в диапазон [-1, 1] (0 — нейтральное значение),
вклад фактора = вес × нормировка. Итоговый балл ограничен [0, 100]
и сравнивается с порогами решения.
"""

SCORING_BASE = 30.0
SCORING_WEIGHTS = {
    "business_age": 15.0,      # стаж бизнеса
    "margin": 20.0,            # рентабельность: прибыль / выручка
    "payment_burden": 25.0,    # долговая нагрузка: платёж / выручка
    "amount_coverage": 10.0,   # запрошенная сумма / годовая выручка
}

# Пороги решения
APPROVE_SCORE = 70.0      # балл >= порога — одобрение
CONDITIONS_SCORE = 50.0   # балл >= порога, но < одобрения — иные условия; ниже — отказ

# Нормировка стажа: 3 года и больше — максимальный балл фактора
BUSINESS_AGE_FULL_MONTHS = 36

# Нормировка рентабельности: 30% и выше — максимум фактора
MARGIN_FULL_RATIO = 0.30

# Нормировка долговой нагрузки (платёж / выручка в месяц):
# до 10% — комфортно (+1), от 50% — критично (-1), линейно между
BURDEN_COMFORT_RATIO = 0.10
BURDEN_CRITICAL_RATIO = 0.50

# Нормировка соотношения суммы к годовой выручке:
# до 0.5 — комфортно (+1), от 2.0 — критично (-1), линейно между
COVERAGE_COMFORT_RATIO = 0.50
COVERAGE_CRITICAL_RATIO = 2.00

# Для решения «одобрение с иными условиями»: подбираем сумму
# под целевую долговую нагрузку
TARGET_BURDEN_RATIO = 0.25

# Округление предложенной суммы вниз, до шага
SUGGESTED_AMOUNT_STEP = 10_000

# Поля профиля, обязательные для скоринга
REQUIRED_PROFILE_FIELDS = ("business_age_months", "monthly_revenue", "monthly_profit")

DECISION_APPROVED = "approved"
DECISION_APPROVED_WITH_CHANGES = "approved_with_changes"
DECISION_REJECTED = "rejected"
DECISION_NEEDS_INFO = "needs_info"

FACTOR_LABELS = {
    "business_age": "Стаж бизнеса",
    "margin": "Рентабельность",
    "payment_burden": "Долговая нагрузка",
    "amount_coverage": "Сумма к годовой выручке",
}

CLAMP_LOW = -1.0
CLAMP_HIGH = 1.0