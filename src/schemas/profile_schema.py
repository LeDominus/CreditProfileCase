from dataclasses import dataclass, field
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict


@dataclass
class BusinessProfile:
    business_name: str | None
    industry: str
    funding_purpose: str
    requested_amount: float | None
    business_age_months: int
    monthly_revenue: float | None
    monthly_profit: float | None
    preferred_term_months: int
    max_monthly_payment: float | None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: int | None = None

class ProfileRequest(BaseModel):
    """PATCH-модель: все поля опциональны — обновляются только переданные"""
    model_config = ConfigDict(extra="forbid")

    business_name: str | None = None
    industry: str | None = None
    funding_purpose: str | None = None
    requested_amount: float | None = None
    business_age_months: int | None = None
    monthly_revenue: float | None = None
    monthly_profit: float | None = None
    preferred_term_months: int | None = None
    max_monthly_payment: float | None = None


class ProfileCreateRequest(BaseModel):
    """Модель создания профиля: ключевые бизнес-поля обязательны, остальные опциональны."""
    model_config = ConfigDict(extra="forbid")

    business_name: str | None = None
    industry: str
    funding_purpose: str
    requested_amount: float | None = None
    business_age_months: int
    monthly_revenue: float | None = None
    monthly_profit: float | None = None
    preferred_term_months: int
    max_monthly_payment: float | None = None