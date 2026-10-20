import os

os.environ.setdefault("YANDEX_API_KEY", "test-key")
os.environ.setdefault("YANDEX_FOLDER", "test-folder")

import pytest

from src.config.sql_queries import (
    CREATE_APPLICATIONS_TABLE,
    CREATE_AUTH_TOKENS_TABLE,
    CREATE_BUSINESS_PROFILES_TABLE,
    CREATE_CONVERSATIONS_TABLE,
    CREATE_MESSAGES_TABLE,
    CREATE_USERS_TABLE,
)
from src.core.applications import ApplicationRepository
from src.core.auth.auth import AuthRepository
from src.core.conversations import ConversationRepository
from src.core.llm.LLMApi import LLMApi
from src.core.profile import ProfileRepository
from src.database.database import DatabaseConnector


@pytest.fixture()
def temp_db(tmp_path):
    """Изолированная SQLite-БД во временной папке со созданными таблицами."""
    db = DatabaseConnector(db_uri=f"sqlite:///{tmp_path / 'test.db'}")
    with db as conn:
        conn.load_data(CREATE_CONVERSATIONS_TABLE)
        conn.load_data(CREATE_MESSAGES_TABLE)
        conn.load_data(CREATE_BUSINESS_PROFILES_TABLE)
        conn.load_data(CREATE_APPLICATIONS_TABLE)
        conn.load_data(CREATE_USERS_TABLE)
        conn.load_data(CREATE_AUTH_TOKENS_TABLE)
    return db


@pytest.fixture()
def profile_repo(temp_db):
    return ProfileRepository(dbConn=temp_db)


@pytest.fixture()
def app_repo(temp_db):
    return ApplicationRepository(dbConn=temp_db)


@pytest.fixture()
def auth_repo(temp_db):
    return AuthRepository(dbConn=temp_db)


@pytest.fixture()
def conv_repo(temp_db):
    return ConversationRepository(dbConn=temp_db)


def authorize_client(client, username: str = "tester") -> None:
    """Регистрирует пользователя и ставит его токен в заголовки клиента по умолчанию.

    Диалоги и профили привязаны к user_id, поэтому всем клиентским фикстурам
    нужен действительный Bearer-токен.
    """
    token = client.post(
        "/api/auth/register",
        json={"username": username, "password": "secret123"},
    ).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})


class StubLLM(LLMApi):
    """Стаб LLM без сетевых вызовов: возвращает заранее заданный ответ."""

    def __init__(self, answer: str = '{"funding_purpose": "Развитие бизнеса"}'):
        self.answer = answer
        self.requests: list[list[dict]] = []
        self.kwargs: list[dict] = []

    def complete(self, context, temperature=None, max_tokens=None, reasoning_effort=None):
        self.requests.append(context)
        self.kwargs.append(
            {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "reasoning_effort": reasoning_effort,
            }
        )
        return self.answer


class ChatStubLLM(LLMApi):
    """Стаб LLM для конвейера сообщений: различает задачи по system-промпту.
    На промпт извлечения профиля отвечает JSON, на обычный диалог — текстом.
    """

    def __init__(
        self,
        extraction_answer: str = '{"requested_amount": 2000000, "preferred_term_months": 18}',
        chat_answer: str = "Расскажите подробнее о вашем бизнесе.",
    ):
        self.extraction_answer = extraction_answer
        self.chat_answer = chat_answer
        self.requests: list[list[dict]] = []

    def complete(self, context, temperature=None, max_tokens=None, reasoning_effort=None):
        self.requests.append(context)
        system = context[0]["content"] if context else ""
        if "извлекатель" in system:
            return self.extraction_answer
        return self.chat_answer


@pytest.fixture()
def stub_llm():
    return StubLLM()