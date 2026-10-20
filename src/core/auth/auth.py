from datetime import datetime, timezone
import secrets
from src.config.sql_queries import (
    CREATE_AUTH_TOKEN_QUERY,
    CREATE_USER_QUERY,
    GET_USER_BY_ID_QUERY,
    GET_USER_BY_TOKEN_QUERY,
    GET_USER_BY_USERNAME_QUERY,
)
from src.database.database import DatabaseConnector
from src.schemas.auth_schema import User
from src.exceptions import *


class AuthRepository:
    """Репозиторий пользователей и токенов"""

    def __init__(self, dbConn: DatabaseConnector):
        self.dbConn: DatabaseConnector = dbConn

    def create_user(self, username: str, password_hash: str, salt: str, role: str) -> int:
        """Создание пользователя. Возвращает id, сгенерированный БД."""
        with self.dbConn as conn:
            return conn.load_data(
                sqlQuery=CREATE_USER_QUERY,
                parameters={
                    "username": username,
                    "password_hash": password_hash,
                    "salt": salt,
                    "role": role,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )

    def get_user_by_username(self, username: str) -> tuple[User, str, str] | None:
        """Пользователь с хешем пароля и солью"""
        with self.dbConn as conn:
            rows = conn.read_data(
                sqlQuery=GET_USER_BY_USERNAME_QUERY,
                parameters={"username": username},
            )
        if not rows:
            return None
        row = rows[0]
        return User(
            id=row["id"],
            username=row["username"],
            role=row["role"],
            created_at=datetime.fromisoformat(row["created_at"]),
        ), row["password_hash"], row["salt"]

    def get_user_by_id(self, user_id: int) -> User | None:
        with self.dbConn as conn:
            rows = conn.read_data(sqlQuery=GET_USER_BY_ID_QUERY, parameters={"id": user_id})
        if not rows:
            return None
        row = rows[0]
        return User(
            id=row["id"],
            username=row["username"],
            role=row["role"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


    def create_token(self, user_id: int) -> str:
        """Создание токена сессии для пользователя."""
        token = secrets.token_hex(32)
        with self.dbConn as conn:
            conn.load_data(
                sqlQuery=CREATE_AUTH_TOKEN_QUERY,
                parameters={
                    "token": token,
                    "user_id": user_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        return token

    def get_user_by_token(self, token: str) -> User | None:
        """Пользователь по токену сессии (None, если токен неизвестен)."""
        with self.dbConn as conn:
            rows = conn.read_data(sqlQuery=GET_USER_BY_TOKEN_QUERY, parameters={"token": token})
        if not rows:
            return None
        row = rows[0]
        return User(
            id=row["id"],
            username=row["username"],
            role=row["role"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

