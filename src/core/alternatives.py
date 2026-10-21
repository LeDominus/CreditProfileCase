from src.config.products import PRODUCTS, MAX_ALTERNATIVE_PRODUCTS
from src.core.calc_payment import calculate_annuity_payment
from src.utils import clamp


def suggest_alternative_products(
    profile: dict,
    exclude_product_id: int | None = None,
    limit: int | None = None,
    products: list[dict] | None = None,
) -> list[dict]:
    """Выдача альтернативных продуктов"""
    catalog = products if products is not None else PRODUCTS
    amount = profile.get("requested_amount")
    term = profile.get("preferred_term_months")
    age = profile.get("business_age_months")
    purpose = (profile.get("funding_purpose") or "").strip().lower()
    max_payment = profile.get("max_monthly_payment")

    matched = []
    for product in catalog:
        if exclude_product_id is not None and product["id"] == exclude_product_id:
            continue
        if amount is None or term is None:
            continue
        if age is not None and age < product["min_age"]:
            continue

        alt_amount = clamp(
            float(amount), float(product["min_amount"]), float(product["max_amount"])
        )
        alt_term = int(clamp(int(term), int(product["min_term"]), int(product["max_term"])))
        monthly = calculate_annuity_payment(alt_amount, float(product["rate"]), alt_term)
        total = round(monthly * alt_term, 4)
        overpayment = round(total - alt_amount, 4)

        product_purpose = (product.get("purpose") or "").lower()
        purpose_match = bool(purpose) and (
            product_purpose in purpose
            or purpose in product_purpose
            or product_purpose == "любые бизнес-цели"
        )
        affordable = max_payment is None or monthly <= float(max_payment)

        matched.append(
            {
                "id": product["id"],
                "name": product["name"],
                "tagline": product.get("tagline", ""),
                "rate": product["rate"],
                "amount": alt_amount,
                "term_months": alt_term,
                "monthly_payment": monthly,
                "total_repayment": total,
                "overpayment": overpayment,
                "amount_reduced": alt_amount < float(amount),
                "affordable": affordable,
                "purpose_match": purpose_match,
            }
        )

    matched.sort(
        key=lambda item: (
            not item["purpose_match"],
            not item["affordable"],
            abs(item["amount"] - float(amount)),
            item["rate"],
        )
    )
    max_count = MAX_ALTERNATIVE_PRODUCTS if limit is None else limit
    return matched[:max_count]