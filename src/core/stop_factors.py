from src.core.registry import get_registry_entry
from src.config.stop_factors_config import *

def find_stop_factors(client_data: dict | None) -> list[dict]:
    """Стоп-факторы по пакету данных клиента; пустой список — проверка пройдена."""
    if not client_data:
        return []
    found = []
    inn = (client_data.get("company") or {}).get("inn") or ""
    entry = get_registry_entry(inn) if inn else None
    if entry is not None and entry.get("liquidation"):
        found.append(STOP_FACTOR_LIQUIDATION)
    if (client_data.get("finance") or {}).get("has_debts"):
        found.append(STOP_FACTOR_DEBTS)
    return [{"code": code, "label": STOP_FACTOR_LABELS[code]} for code in found]