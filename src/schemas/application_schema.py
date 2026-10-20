
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict


STATUS_SUBMITTED = "submitted" # создана клиентом
STATUS_SCORING = "scoring"  # на скоринге (банковская сторона)
STATUS_APPROVED = "approved" # одобрена
STATUS_APPROVED_WITH_CHANGES = "approved_with_changes" # одобрена с иными условиями
STATUS_REJECTED = "rejected" # отказ
STATUS_NEEDS_INFO = "needs_info" # нужны уточнения по профилю
STATUS_ISSUED = "issued" # выдана (выдача смоделирована)

APPLICATION_STATUSES = [
    STATUS_SUBMITTED,
    STATUS_SCORING,
    STATUS_APPROVED,
    STATUS_APPROVED_WITH_CHANGES,
    STATUS_REJECTED,
    STATUS_NEEDS_INFO,
    STATUS_ISSUED,
]

ALLOWED_TRANSITIONS = {
    STATUS_SUBMITTED: {STATUS_SCORING},
    STATUS_SCORING: {
        STATUS_APPROVED,
        STATUS_APPROVED_WITH_CHANGES,
        STATUS_REJECTED,
        STATUS_NEEDS_INFO,
    },
    STATUS_NEEDS_INFO: {STATUS_SCORING}, # повторный скоринг после уточнения
    STATUS_APPROVED: {STATUS_ISSUED}, # финальное подтверждение клиента
    STATUS_APPROVED_WITH_CHANGES: {STATUS_ISSUED},
    STATUS_REJECTED: set(),
    STATUS_ISSUED: set(),
}


def can_transition(current: str, target: str) -> bool:
    """Разрешён ли переход статуса заявки"""
    return target in ALLOWED_TRANSITIONS.get(current, set())


@dataclass
class Application:
    """Заявка на кредитный продукт"""
    profile_id: int
    product_id: int
    product_name: str
    requested_amount: float
    term_months: int
    monthly_payment: float
    total_repayment: float
    overpayment: float
    status: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    score: float | None = None
    decision: str | None = None
    decision_details: dict | None = None 
    id: int | None = None


class ApplicationCreateRequest(BaseModel):
    """Создание заявки: профиль + продукт + параметры"""
    model_config = ConfigDict(extra="forbid")
    profile_id: int
    product_id: int
    requested_amount: float
    term_months: int


class ApplicationConfirmRequest(BaseModel):
    """Финальное подтверждение клиентом решения по заявке"""
    model_config = ConfigDict(extra="forbid")
    confirmed: bool