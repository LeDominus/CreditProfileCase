import json
import logging
import re
from src.config.prompt import PROFILE_EXTRACTION_PROMPT
from src.config.llm_config import PROFILE_FIELDS
from src.core.llm.LLMApi import LLMApi

logger = logging.getLogger(__name__)

# Температура извлечения полей: 0.15 — при 0.0 ответы слишком сухие
# (не зависит от env TEMPERATURE, чтобы поведение было детерминированным)
EXTRACTION_TEMPERATURE = 0.15


def extract_profile_fields(
    message: str,
    llm: LLMApi,
    current_profile: dict | None = None,
) -> dict:
    """Принимает сообщение пользователя и возвращает структурированные поля профиля"""
    if not message or not message.strip():
        return {}
    context = llm.extract_context(
        messages=[{"role": "user", "content": message}],
        profile=current_profile,
        system_prompt=PROFILE_EXTRACTION_PROMPT,
    )
    logger.info("Извлечение полей профиля: отправка запроса к LLM…")
    try:
        raw_answer = llm.complete(
            context, temperature=EXTRACTION_TEMPERATURE, reasoning_effort="none"
        )
    except Exception as exc:
        logger.warning("Извлечение полей профиля: LLM недоступна (%s)", exc)
        return {}
    fields = parse_profile_fields(raw_answer)
    if fields:
        logger.info(
            "Извлечение полей профиля: получено полей — %d: %s",
            len(fields),
            ", ".join(sorted(fields)),
        )
    else:
        logger.info("Извлечение полей профиля: новых полей не распознано")
    return fields


def parse_profile_fields(raw_answer: str) -> dict:
    """Разбор ответа LLM: извлечение JSON и валидация полей профиля"""
    if not raw_answer:
        return {}
    match = re.search(r"\{.*\}", raw_answer, re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    result = {}
    for key, expected_type in PROFILE_FIELDS.items():
        value = data.get(key)
        if value is None:
            continue
        try:
            if expected_type is float:
                result[key] = float(value)
            elif expected_type is int:
                result[key] = int(float(value))
            else:
                text = str(value).strip()
                if text:
                    result[key] = text
        except (TypeError, ValueError):
            continue
    return result