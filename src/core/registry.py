from src.database.registry import REGISTRY_ENTRIES


def get_registry_entry(inn: str) -> dict | None:
    """Запись тестового реестра по ИНН компании или None, если ИНН неизвестен."""
    return next((entry for entry in REGISTRY_ENTRIES if entry["inn"] == inn), None)
