
from src.config.llm_config import PROFILE_FIELDS
from src.schemas.profile_schema import BusinessProfile


FALLBACK_REPLY = (
    "Сообщение принято. Ассистент временно недоступен — "
    "продолжу помогать, как только связь восстановится."
)


def profile_to_dict(profile: BusinessProfile) -> dict:
    """Профиль в виде словаря полей из PROFILE_FIELDS"""
    return {field: getattr(profile, field) for field in PROFILE_FIELDS}