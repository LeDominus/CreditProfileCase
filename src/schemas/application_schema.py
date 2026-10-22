from dataclasses import dataclass, field
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.schemas.profile_schema import ClientDataRequest


STATUS_DRAFT = "draft"  # черновик: заявка сохранена, не отправлена
STATUS_SUBMITTED = "submitted"  # отправлена клиентом в банк
STATUS_DATA_CHECK = "data_check"  # проверка данных: сбор сведений, стоп-факторы
STATUS_SCORING = "scoring"  # автоматический скоринг
STATUS_NEEDS_INFO = "needs_info"  # нужны уточнения по профилю
STATUS_MANUAL_REVIEW = "manual_review"  # ручная экспертиза (кредитный аналитик)
STATUS_APPROVED = "approved"  # одобрена на запрошенных условиях
STATUS_APPROVED_WITH_CHANGES = "approved_with_changes"  # одобрена на иных условиях
STATUS_REJECTED = "rejected"  # отказ (терминальный)
STATUS_OFFER_READY = "offer_ready"  # предложение сформировано, ждёт решения клиента
STATUS_ACCEPTED = "accepted"  # клиент принял условия предложения
STATUS_SIGNED = "signed"  # подписана клиентом (ЭП моделируется кнопкой)
STATUS_ISSUED = "issued"  # выдана (терминальный)
STATUS_CLIENT_DECLINED = "client_declined"  # клиент отказался от предложения (терминальный)

APPLICATION_STATUSES = [
    STATUS_DRAFT,
    STATUS_SUBMITTED,
    STATUS_DATA_CHECK,
    STATUS_SCORING,
    STATUS_NEEDS_INFO,
    STATUS_MANUAL_REVIEW,
    STATUS_APPROVED,
    STATUS_APPROVED_WITH_CHANGES,
    STATUS_REJECTED,
    STATUS_OFFER_READY,
    STATUS_ACCEPTED,
    STATUS_SIGNED,
    STATUS_ISSUED,
    STATUS_CLIENT_DECLINED,
]

# Матрица допустимых переходов
ALLOWED_TRANSITIONS = {
    STATUS_DRAFT: {STATUS_SUBMITTED},
    STATUS_SUBMITTED: {STATUS_DATA_CHECK},
    STATUS_DATA_CHECK: {
        STATUS_SCORING,
        STATUS_REJECTED,  # стоп-факторы (п. 2.6)
        STATUS_NEEDS_INFO,
        STATUS_MANUAL_REVIEW,  # передача аналитику менеджером (п. 2.5)
    },
    STATUS_SCORING: {
        STATUS_APPROVED,
        STATUS_APPROVED_WITH_CHANGES,
        STATUS_REJECTED,
        STATUS_NEEDS_INFO,
        STATUS_MANUAL_REVIEW,
    },
    STATUS_NEEDS_INFO: {STATUS_DATA_CHECK},  # повторная обработка с единого входа
    STATUS_MANUAL_REVIEW: {
        STATUS_APPROVED,
        STATUS_APPROVED_WITH_CHANGES,
        STATUS_REJECTED,
        STATUS_NEEDS_INFO,  # запрос уточнений менеджером (п. 2.5)
    },
    STATUS_APPROVED: {STATUS_OFFER_READY},
    STATUS_APPROVED_WITH_CHANGES: {STATUS_OFFER_READY},
    STATUS_OFFER_READY: {STATUS_ACCEPTED, STATUS_CLIENT_DECLINED},
    STATUS_ACCEPTED: {STATUS_SIGNED},
    STATUS_SIGNED: {STATUS_ISSUED},
    STATUS_REJECTED: set(),
    STATUS_ISSUED: set(),
    STATUS_CLIENT_DECLINED: set(),
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
    client_data: dict | None = None
    id: int | None = None


class ApplicationCreateRequest(BaseModel):
    """Создание заявки: профиль + продукт + параметры + пакет данных клиента"""
    model_config = ConfigDict(extra="forbid")
    profile_id: int
    product_id: int
    requested_amount: float
    term_months: int
    client_data: ClientDataRequest | None = None


class ApplicationUpdateRequest(BaseModel):
    """Редактирование черновика: сумма/срок (оба опциональны, но хотя бы одно)"""
    model_config = ConfigDict(extra="forbid")
    requested_amount: float | None = None
    term_months: int | None = None

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        if self.requested_amount is None and self.term_months is None:
            raise ValueError(
                "At least one of requested_amount or term_months must be provided"
            )
        return self


class ApplicationOfferResponseRequest(BaseModel):
    """Отклик клиента на предложение: принять или отклонить (с причиной)"""
    model_config = ConfigDict(extra="forbid")
    accept: bool
    decline_reason: str | None = None


# Аудитории ИИ-объяснения решения по заявке (п. 2.8 плана MVP)
EXPLAIN_AUDIENCES = ("client", "analyst")


class ApplicationExplainRequest(BaseModel):
    """Запрос ИИ-объяснения решения: для клиента или сводка для аналитика"""
    model_config = ConfigDict(extra="forbid")
    audience: str = "client"  # client | analyst

    @model_validator(mode="after")
    def check_audience(self):
        if self.audience not in EXPLAIN_AUDIENCES:
            raise ValueError(
                f"audience must be one of {EXPLAIN_AUDIENCES} (got: {self.audience!r})"
            )
        return self


# Решения кредитного аналитика по заявке в ручной экспертизе (п. 2.5)
ANALYST_DECISIONS = (STATUS_APPROVED, STATUS_APPROVED_WITH_CHANGES, STATUS_REJECTED)


class AdminRequestInfoRequest(BaseModel):
    """Запрос уточнений менеджером банка: data_check|scoring|manual_review -> needs_info"""
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=3, max_length=1000)


class AdminDecisionRequest(BaseModel):
    """Решение кредитного аналитика по заявке в ручной экспертизе (с причиной)"""
    model_config = ConfigDict(extra="forbid")

    decision: str
    reason: str = Field(min_length=3, max_length=1000)

    @model_validator(mode="after")
    def check_decision(self):
        if self.decision not in ANALYST_DECISIONS:
            raise ValueError(
                f"decision must be one of {ANALYST_DECISIONS} (got: {self.decision!r})"
            )
        return self
