import logging
from src.config.prompt import EXPLAIN_ANALYST_PROMPT, EXPLAIN_CLIENT_PROMPT
from src.core.llm.LLMApi import LLMApi
from src.config.llm_config import EXPLAIN_TEMPERATURE, EXPLAIN_SOURCE_FALLBACK, EXPLAIN_SOURCE_LLM
from src.schemas.application_schema import EXPLAIN_AUDIENCES

logger = logging.getLogger(__name__)


def explain_application_decision(
    llm: LLMApi,
    application: dict,
    audience: str = "client",
) -> dict:
    """Объяснение решения по заявке для клиента или аналитика"""
    if audience not in EXPLAIN_AUDIENCES:
        raise ValueError(
            f"Unknown audience: {audience!r} (expected one of {EXPLAIN_AUDIENCES})"
        )
    system_prompt = (
        EXPLAIN_CLIENT_PROMPT if audience == "client" else EXPLAIN_ANALYST_PROMPT
    )
    context = llm.extract_context(
        messages=[{"role": "user", "content": _decision_brief(application)}],
        system_prompt=system_prompt,
    )
    answer = ""
    try:
        logger.info("Объяснение решения (%s): запрос к LLM…", audience)
        answer = llm.complete(
            context, temperature=EXPLAIN_TEMPERATURE, reasoning_effort="low"
        )
    except Exception as exc:
        logger.warning("Объяснение решения: LLM недоступна (%s) — fallback", exc)
    if answer and answer.strip():
        return {
            "audience": audience,
            "explanation": answer.strip(),
            "source": EXPLAIN_SOURCE_LLM,
        }
    logger.info("Объяснение решения (%s): собран детерминированный fallback", audience)
    return {
        "audience": audience,
        "explanation": _fallback_explanation(application, audience),
        "source": EXPLAIN_SOURCE_FALLBACK,
    }


def _decision_brief(application: dict) -> str:
    """Компактный блок «Данные решения» — единственный источник для LLM."""
    details = application.get("decision_details") or {}
    lines = [
        "Данные решения:",
        f"- Продукт: {application.get('product_name')}",
        f"- Запрошено: {application.get('requested_amount')} руб. "
        f"на {application.get('term_months')} мес.",
        f"- Статус заявки: {application.get('status')}",
        f"- Решение скоринга: {details.get('decision')}",
        f"- Балл скоринга: {details.get('score')}",
    ]
    if details.get("missing_fields"):
        lines.append(
            "- Незаполненные поля профиля: " + ", ".join(details["missing_fields"])
        )
    if details.get("suggested_amount") is not None:
        term_hint = (
            f" на {details['suggested_term_months']} мес."
            if details.get("suggested_term_months") is not None
            else ""
        )
        lines.append(
            f"- Предложенные условия: {details['suggested_amount']} руб.{term_hint}, "
            f"платёж {details.get('suggested_monthly_payment')} руб./мес"
        )
    factors = details.get("factors") or []
    if factors:
        lines.append("- Факторы скоринга:")
        lines.extend(
            f"  * {f.get('label', f.get('name'))}: {f.get('value')} "
            f"(вклад в балл: {f.get('contribution')})"
            for f in factors
        )
    if details.get("explanation"):
        lines.append(f"- Формулировка системы: {details['explanation']}")
    return "\n".join(lines)


def _fallback_explanation(application: dict, audience: str) -> str:
    """Детерминированное объяснение из decision_details (без LLM)."""
    details = application.get("decision_details") or {}
    parts = []
    base = (details.get("explanation") or "").strip()
    if base:
        parts.append(base)
    factors = details.get("factors") or []
    if factors:
        weakest = sorted(factors, key=lambda f: f.get("contribution") or 0.0)[:2]
        parts.append(
            "Сильнее всего на решение повлияли: "
            + "; ".join(f"{f.get('label')} ({f.get('value')})" for f in weakest)
            + "."
        )
    if details.get("missing_fields"):
        parts.append(
            "Для точного решения не хватает данных: "
            + ", ".join(details["missing_fields"])
            + "."
        )
    if audience == "analyst":
        parts.append(
            "Стоп-факторы не зафиксированы: этап проверки данных пройден автоматически."
        )
    if not parts:
        parts.append("Решение по заявке пока не сформировано.")
    return " ".join(parts)