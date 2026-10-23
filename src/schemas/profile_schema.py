from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


INN_PATTERN = r"^\d{10}(\d{2})?$"
PERSON_INN_PATTERN = r"^\d{12}$"
PHONE_PATTERN = r"^\+7\d{10}$"
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


@dataclass
class BusinessProfile:
    business_name: str | None
    industry: str
    funding_purpose: str
    requested_amount: float | None
    business_age_months: int | None
    monthly_revenue: float | None
    monthly_profit: float | None
    preferred_term_months: int | None
    max_monthly_payment: float | None
    user_id: int | None = None
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
    """Модель создания профиля: ключевые бизнес-поля обязательны, остальные опциональны.

    business_age_months и preferred_term_months опциональны: профиль создаётся
    при первом сообщении диалога, когда стаж бизнеса и срок ещё не названы
    (в БД колонки nullable, скоринг до уточнения вернёт needs_info).
    """
    model_config = ConfigDict(extra="forbid")

    business_name: str | None = None
    industry: str
    funding_purpose: str
    requested_amount: float | None = None
    business_age_months: int | None = None
    monthly_revenue: float | None = None
    monthly_profit: float | None = None
    preferred_term_months: int | None = None
    max_monthly_payment: float | None = None


class CreditRequest(BaseModel):
    """Раздел «О кредите»: параметры кредита, которые вводит клиент"""
    model_config = ConfigDict(extra="forbid")

    credit_product: Literal["оборотный кредит", "инвестиционный кредит", "овердрафт"]
    credit_sum: float = Field(gt=0)
    credit_term_months: int = Field(gt=0)
    credit_target: str = Field(min_length=1)


class CompanyRequest(BaseModel):
    """Раздел «О компании»: реквизиты из реестра по ИНН и данные, которые вводит клиент"""
    model_config = ConfigDict(extra="forbid")

    inn: str = Field(pattern=INN_PATTERN)
    company_name: str
    ogrn: str
    registered_address: str
    registration_date: datetime
    type_of_activity: str
    company_supervisor: str
    company_members: list[str]
    company_place: str
    taxation_system: str
    company_members_count: int = Field(gt=0)
    company_phone: str = Field(pattern=PHONE_PATTERN)
    company_email: str = Field(pattern=EMAIL_PATTERN)


class SupervisorRequest(BaseModel):
    """Раздел «О руководителе»: ФИО из реестра по ИНН, остальные данные вводит клиент"""
    model_config = ConfigDict(extra="forbid")

    full_name: str
    passport: str
    passport_issued_by: str
    place_of_birth: str
    citizenship: str = "russian"
    registration_address: str
    inn_fiz_face: str = Field(pattern=PERSON_INN_PATTERN)
    supervisor_phone: str = Field(pattern=PHONE_PATTERN)
    supervisor_email: str = Field(pattern=EMAIL_PATTERN)
    owners_full_name: list[str] | None = None
    owners_passport: list[str] | None = None


class FinanceRequest(BaseModel):
    """Раздел «О финансах»: показатели за последний год, которые вводит клиент"""
    model_config = ConfigDict(extra="forbid")

    revenue: float = Field(ge=0)
    profit: float
    current_loans_and_leasing: list[str] | None = None
    has_debts: bool


class DocumentsRequest(BaseModel):
    """Раздел «Документы»: имена файлов, загруженных клиентом"""
    model_config = ConfigDict(extra="forbid")

    supervisor_passport_scan: str
    business_type: Literal["ip", "ooo"]
    business_doc: list[str]


class ConsentRequest(BaseModel):
    """Раздел «Согласия»: обязательные галочки в заявке"""
    model_config = ConfigDict(extra="forbid")

    personal_data_agreement: bool
    credit_history_agreement: bool

    @model_validator(mode="after")
    def check_agreements_accepted(self):
        if not (self.personal_data_agreement and self.credit_history_agreement):
            raise ValueError(
                "personal_data_agreement and credit_history_agreement must be accepted"
            )
        return self


class ClientDataRequest(BaseModel):
    """Полный пакет данных клиента для отправки заявки на кредит"""
    model_config = ConfigDict(extra="forbid")

    credit: CreditRequest
    company: CompanyRequest
    supervisor: SupervisorRequest
    finance: FinanceRequest
    documents: DocumentsRequest
    consents: ConsentRequest
