from src.config.products import MAX_RECOMMEND_PRODUCTS, PRODUCTS
from src.core.calc_payment import calculate_annuity_payment

def recommend_products(
    profile: dict,
    products: list[dict] | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Возвращает до `limit` (по умолчанию MAX_RECOMMEND_PRODUCTS) продуктов,
    подходящих под профиль"""

    catalog = products if products is not None else PRODUCTS
    amount = profile.get("requested_amount")
    term = profile.get("preferred_term_months")
    age = profile.get("business_age_months")
    purpose = (profile.get("funding_purpose") or "").strip().lower()
    max_payment = profile.get("max_monthly_payment")

    matched = []
    for product in catalog:
        if amount is not None and not product["min_amount"] <= amount <= product["max_amount"]:
            continue
        if term is not None and not product["min_term"] <= term <= product["max_term"]:
            continue
        if age is not None and age < product["min_age"]:
            continue

        calc_amount = float(amount) if amount is not None else float(product["min_amount"])
        calc_term = int(term) if term is not None else int(product["min_term"])
        monthly = calculate_annuity_payment(calc_amount, float(product["rate"]), calc_term)
        total = round(monthly * calc_term, 4)
        overpayment = round(total - calc_amount, 4)

        product_purpose = (product.get("purpose") or "").lower()
        purpose_match = bool(purpose) and (
            product_purpose in purpose
            or purpose in product_purpose
            or product_purpose == "любые бизнес-цели"
        )
        affordable = max_payment is None or monthly <= float(max_payment)

        matched.append(
            {
                **product,
                "monthly_payment": monthly,
                "total_repayment": total,
                "overpayment": overpayment,
                "affordable": affordable,
                "purpose_match": purpose_match,
            }
        )

    matched.sort(key=lambda item: (not item["purpose_match"], not item["affordable"], item["rate"]))
    max_count = MAX_RECOMMEND_PRODUCTS if limit is None else limit
    return matched[:max_count]
