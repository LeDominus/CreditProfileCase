from dataclasses import dataclass, field


@dataclass
class ContractExtraction:
    """Результат LLM-конвейера обработки сообщения (тело ответа API)."""
    status: str
    id: int
    assistant_message_id: int
    conversation_id: int
    reply: str
    profile_updates: dict
    profile: dict | None = None
    recommendations: list[dict] = field(default_factory=list)


@dataclass
class ToolExecution:
    """Результат детерминированного исполнения инструмента LLM.

    При status="error" заполнено только error, числовые поля — None.
    """
    status: str
    tool: str = ""
    error: str | None = None
    amount: float | None = None
    annual_rate: float | None = None
    months: int | None = None
    monthly_payment: float | None = None
    total_repayment: float | None = None
    overpayment: float | None = None