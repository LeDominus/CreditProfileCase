
MIGRATIONS = (
    "ALTER TABLE conversations ADD COLUMN user_id INTEGER",
    "ALTER TABLE business_profiles ADD COLUMN user_id INTEGER",
)


def apply_migrations(conn) -> None:
    """Применяет миграции; повторный запуск безопасен (колонка уже есть — пропускаем)."""
    for sql in MIGRATIONS:
        try:
            conn.load_data(sql)
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                raise
