import json
import logging
import re
from src.config.prompt import PROFILE_EXTRACTION_PROMPT
from src.config.llm_config import (
    DURATION_MONTH_FIELDS,
    EXTRACTION_TEMPERATURE,
    MODEL_EXTRACTION,
    PROFILE_FIELDS,
)
from src.core.llm.LLMApi import LLMApi

logger = logging.getLogger(__name__)

# Разговорные дробные числа («полтора года»)
_FRACTION_YEARS = {"полтора": 1.5, "полторы": 1.5}
_YEAR_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:год|года|лет|годов|г)\b")
_MONTH_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:месяц\w*|мес\w*|м)\b")


def parse_duration_months(value) -> int | None:
    """Число месяцев из значения LLM: 24, «24», «2 года», «полтора года», «1 год 6 месяцев».

    Возвращает None, если значение не распознано как длительность.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().lower().replace(",", ".")
    if not text:
        return None
    total = 0.0
    matched = False
    for word, years in _FRACTION_YEARS.items():
        if word in text:
            total += years * 12
            matched = True
            text = text.replace(word, " ")
    for match in _YEAR_PATTERN.finditer(text):
        total += float(match.group(1)) * 12
        matched = True
    for match in _MONTH_PATTERN.finditer(text):
        total += float(match.group(1))
        matched = True
    if not matched:
        # просто число без единиц («24»)
        try:
            return int(float(text))
        except ValueError:
            return None
    months = int(round(total))
    return months if months > 0 else None


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
            context,
            temperature=EXTRACTION_TEMPERATURE,
            reasoning_effort="low",
            model=MODEL_EXTRACTION,
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
    return validate_profile_fields(data)


def validate_profile_fields(data) -> dict:
    """Валидация полей профиля из dict (ответ извлекателя или диалоговой модели)"""
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
                if key in DURATION_MONTH_FIELDS:
                    months = parse_duration_months(value)
                    if months is not None:
                        result[key] = months
                else:
                    result[key] = int(float(value))
            else:
                text = str(value).strip()
                if text:
                    result[key] = text
        except (TypeError, ValueError):
            continue
    return result