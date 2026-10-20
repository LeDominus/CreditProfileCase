from dataclasses import dataclass, field
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field


@dataclass
class User:
    """Пользователь системы"""
    username: str
    role: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: int | None = None


class AuthRegisterRequest(BaseModel):
    """Регистрация: логин, пароль и роль"""
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=4, max_length=128)
    role: str = "client"


class AuthLoginRequest(BaseModel):
    """Вход: логин и пароль."""
    model_config = ConfigDict(extra="forbid")

    username: str
    password: str