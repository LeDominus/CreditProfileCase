import os
from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
)

load_dotenv()

YANDEX_FOLDER = os.getenv('YANDEX_FOLDER')
MODEL_NAME = os.getenv('MODEL_NAME')
FALLBACK_MODEL_NAME = os.getenv('FALLBACK_MODEL_NAME')
EXTRACTION_MODEL_NAME = os.getenv('EXTRACTION_MODEL_NAME')
YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')

MODEL_DIALOGUE = "dialogue"
MODEL_EXTRACTION = "extraction"

MAX_MESSAGES = 20

PROFILE_FIELDS: dict[str, type] = {
    "business_name": str,
    "industry": str,
    "funding_purpose": str,
    "requested_amount": float,
    "business_age_months": int,
    "monthly_revenue": float,
    "monthly_profit": float,
    "preferred_term_months": int,
    "max_monthly_payment": float,
}
DURATION_MONTH_FIELDS = ("business_age_months", "preferred_term_months")

REQUIRED_PROFILE_FIELDS: dict[str, str] = {
    "business_age_months": "срок работы бизнеса в месяцах",
    "monthly_revenue": "выручка в месяц, руб.",
    "monthly_profit": "прибыль в месяц, руб.",
}


def _env_float(name: str, default: float) -> float:
    """Числовая переменная окружения с дефолтом"""
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(float(raw))
    except ValueError:
        return default


TEMPERATURE = _env_float('TEMPERATURE', 0.0)
EXTRACTION_TEMPERATURE = _env_float('EXTRACTION_TEMPERATURE', 0.15)
MAX_OUTPUT_TOKENS = _env_int('MAX_OUTPUT_TOKENS', 10000)
LLM_TIMEOUT = _env_float('LLM_TIMEOUT', 15.0)
BASE_URL = os.getenv('BASE_URL')
EXPLAIN_SOURCE_LLM = "llm"
EXPLAIN_SOURCE_FALLBACK = "fallback"
EXPLAIN_TEMPERATURE = 0.2
REASONING_EFFORT = (os.getenv('REASONING_EFFORT') or 'low').strip().lower()

SDK_UNAVAILABLE_ERRORS = (
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    InternalServerError,
    NotFoundError,
)