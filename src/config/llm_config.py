import os
from dotenv import load_dotenv

load_dotenv()

YANDEX_FOLDER = os.getenv('YANDEX_FOLDER')
MODEL_NAME = os.getenv('MODEL_NAME')
YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')

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

# оля профиля, обязательные для отправки заявки: ассистент уточняет их в диалоге,
# пока все не заполнены — диалог не завершается
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
MAX_OUTPUT_TOKENS = _env_int('MAX_OUTPUT_TOKENS', 2500)
BASE_URL = os.getenv('BASE_URL')

# Глубина рассуждений reasoning-модели: 'none' | 'low' | 'medium' | 'high'.
# 'off' — не отправлять параметр вовсе (поведение по умолчанию у провайдера).
# Замер на deepseek-v4.1-flash (Yandex Cloud): без параметра ~30 сек на вызов,
# 'low' ~22 сек, 'none' ~27 сек — при одинаковых коротких промптах.
REASONING_EFFORT = (os.getenv('REASONING_EFFORT') or 'low').strip().lower()