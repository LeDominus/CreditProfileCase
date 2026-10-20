from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict


@dataclass
class LoadProduct:
    id: int
    name: str
    purpose: float
    min_amount: float
    max_amount: float
    min_term_months: int
    max_term_months: int
    min_business_months_age: int
    annual_rate: float
    is_active: bool


class RecommendationRequest(BaseModel):
    """Профиль бизнеса для подбора продуктов: все поля опциональны"""
    model_config = ConfigDict(extra="ignore")

    business_name: str | None = None
    industry: str | None = None
    funding_purpose: str | None = None
    requested_amount: float | None = None
    business_age_months: int | None = None
    monthly_revenue: float | None = None
    monthly_profit: float | None = None
    preferred_term_months: int | None = None
    max_monthly_payment: float | None = None