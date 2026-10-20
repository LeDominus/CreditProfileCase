from decimal import Decimal

"""
    Текущая реализация - простейшая из возможных, поскольку рассчитывает базовый аннуитетный платеж,
    если в условиях кейса будет иной способ - заменяю его здесь
"""

def calculate_annuity_payment(credit_sum: Decimal, annual_rate: float, months: int) -> float:
    """Расчёт ежемесячного аннуитетного платежа"""
    if credit_sum <= 0:
        raise ValueError("Сумма кредита должна быть больше нуля")
    if annual_rate <= 0:
        raise ValueError("Годовая процентная ставка не может быть меньше или равна нулю")
    if months <= 0:
        raise ValueError("Число месяцев не может быть меньше или равно нулю")

    credit_sum = float(credit_sum)

    monthly_rate = annual_rate / 12 / 100
    coeff = (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)

    return float(round(credit_sum * coeff, 4))