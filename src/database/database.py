import logging
import os
from typing import Any, Dict, List, Optional
from sqlalchemy import CursorResult, Engine, create_engine, Connection, text

logger = logging.getLogger(__name__)


class DatabaseConnector:
    def __init__(self, db_uri: str | None = None, echo: bool | None = None):
        self.db_uri = db_uri or os.getenv("DATABASE_URI", "sqlite:///data/database.db")
        if echo is None:
            echo = os.getenv("DB_ECHO", "false").lower() == "true"
        self._echo = echo
        self._engine: Optional[Engine] = None
        self._init_engine()
        self.connection: Optional[Connection] = None

    def _init_engine(self) -> Engine:
        """Инициализация подключения к БД"""
        try:
            self._engine = create_engine(self.db_uri, echo=self._echo)
            logger.debug("[DatabaseConnector] engine успешно создан")
            return self._engine
        except Exception as e:
            raise ConnectionError(f"Ошибка при подключении к БД: {e}") from e

    def _create_connection(self) -> Connection:
        self.connection = self._engine.connect()
        logger.debug("[DatabaseConnector] Соединение с БД успешно установлено")
        return self.connection

    def __enter__(self):
        if self._engine is None:
            raise RuntimeError("[DatabaseConnector] Engine не инициализирован")
        self.connection = self._engine.connect()
        logger.debug("[DatabaseConnector] Соединение с БД успешно установлено")
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.connection:
            try:
                if exc_type is not None:
                    logger.warning("[DatabaseConnector] Ошибка в блоке: %s. Откатываем транзакцию.", exc)
                self.connection.close()
                logger.debug("[DatabaseConnector] Соединение с БД успешно закрыто")
            except Exception as e:
                logger.error("[DatabaseConnector] Ошибка при закрытии соединения: %s", e)
        return False


    def read_data(self, sqlQuery: str, parameters: dict[str] | None = None) -> List[Dict[str, Any]]:
        """Чтение данных"""
        if not self.connection:
            raise RuntimeError("[DatabaseConnector] Соединение с БД не установлено")

        if sqlQuery is None:
            raise ValueError(f"[DatabaseConnector] Некорретный SQL запрос: {sqlQuery}")

        result: CursorResult = self.connection.execute(text(sqlQuery), parameters=parameters or {})
        logger.debug("[DatabaseConnector] Данные успешно прочитаны")
        return [dict(row) for row in result.mappings().all()]


    def load_data(self, sqlQuery: str, parameters: dict[str] | None = None) -> int | None:
        """Загрузка данных в БД. Возвращает id вставленной строки (lastrowid), если применимо."""
        if not self.connection:
            raise RuntimeError("[DatabaseConnector] Соединение с БД не установлено")

        if sqlQuery is None:
            raise ValueError(f"[DatabaseConnector] Некорретный SQL запрос: {sqlQuery}")

        result = self.connection.execute(text(sqlQuery), parameters=parameters or {})
        self.connection.commit()
        logger.debug("[DatabaseConnector] Данные успешно загружены")
        return result.lastrowid
