from dataclasses import dataclass, field, asdict


@dataclass
class ScoringResult:
    """Результат скоринга: балл, решение, разбор факторов и предложение"""

    score: float | None
    decision: str
    factors: list[dict] = field(default_factory=list)
    explanation: str = ""
    missing_fields: list[str] = field(default_factory=list)
    suggested_amount: float | None = None
    suggested_term_months: int | None = None
    suggested_monthly_payment: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)