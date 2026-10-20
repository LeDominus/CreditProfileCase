"""Тесты авторизации: регистрация, вход, токены, ручки /api/auth/*."""

import pytest
from fastapi.testclient import TestClient

from src.core.auth.auth_service_methods import (
    hash_password,
    login_user,
    register_user,
)
from src.exceptions import InvalidCredentialsError, UsernameTakenError


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URI", f"sqlite:///{tmp_path / 'auth_test.db'}")
    from main import app

    with TestClient(app) as test_client:
        yield test_client


class TestAuthRepository:
    """Юнит-тесты сервисных методов (без HTTP)."""

    def test_register_and_login_roundtrip(self, auth_repo):
        user, token = register_user(auth_repo, "owner1", "secret123")
        assert user.id is not None
        assert user.username == "owner1"
        assert user.role == "client"
        assert len(token) == 64

        logged_in, login_token = login_user(auth_repo, "owner1", "secret123")
        assert logged_in.id == user.id
        assert len(login_token) == 64

    def test_register_duplicate_username(self, auth_repo):
        register_user(auth_repo, "owner1", "secret123")
        with pytest.raises(UsernameTakenError):
            register_user(auth_repo, "owner1", "other456")

    def test_login_wrong_password(self, auth_repo):
        register_user(auth_repo, "owner1", "secret123")
        with pytest.raises(InvalidCredentialsError):
            login_user(auth_repo, "owner1", "wrong")

    def test_login_unknown_user(self, auth_repo):
        with pytest.raises(InvalidCredentialsError):
            login_user(auth_repo, "ghost", "whatever")

    def test_password_hash_is_salted(self, auth_repo):
        """Одинаковые пароли дают разные хеши (разная соль)."""
        assert hash_password("pass", "aa" * 16) != hash_password("pass", "bb" * 16)

    def test_get_user_by_token(self, auth_repo):
        user, token = register_user(auth_repo, "owner1", "secret123")
        found = auth_repo.get_user_by_token(token)
        assert found is not None and found.id == user.id
        assert auth_repo.get_user_by_token("no-such-token") is None


class TestAuthApi:
    """Интеграционные тесты HTTP-ручек /api/auth/*."""

    def test_register_returns_token_and_user(self, client):
        response = client.post(
            "/api/auth/register",
            json={"username": "owner1", "password": "secret123"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "success"
        assert len(body["token"]) == 64
        assert body["user"]["username"] == "owner1"
        assert body["user"]["role"] == "client"
        # хеш пароля не должен попадать в ответ
        assert "password_hash" not in body["user"]

    def test_register_duplicate_409(self, client):
        client.post("/api/auth/register", json={"username": "owner1", "password": "secret123"})
        response = client.post(
            "/api/auth/register", json={"username": "owner1", "password": "other456"}
        )
        assert response.status_code == 409

    def test_register_unknown_role_422(self, client):
        response = client.post(
            "/api/auth/register",
            json={"username": "owner1", "password": "secret123", "role": "admin"},
        )
        assert response.status_code == 422

    def test_register_short_password_422(self, client):
        response = client.post(
            "/api/auth/register", json={"username": "owner1", "password": "abc"}
        )
        assert response.status_code == 422

    def test_register_unknown_field_422(self, client):
        response = client.post(
            "/api/auth/register",
            json={"username": "owner1", "password": "secret123", "hack": 1},
        )
        assert response.status_code == 422

    def test_login_ok(self, client):
        client.post("/api/auth/register", json={"username": "owner1", "password": "secret123"})
        response = client.post(
            "/api/auth/login", json={"username": "owner1", "password": "secret123"}
        )
        assert response.status_code == 200
        assert len(response.json()["token"]) == 64

    def test_login_wrong_password_401(self, client):
        client.post("/api/auth/register", json={"username": "owner1", "password": "secret123"})
        response = client.post(
            "/api/auth/login", json={"username": "owner1", "password": "wrong"}
        )
        assert response.status_code == 401

    def test_me_with_token(self, client):
        token = client.post(
            "/api/auth/register", json={"username": "owner1", "password": "secret123"}
        ).json()["token"]
        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["user"]["username"] == "owner1"

    def test_me_without_token_401(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_with_invalid_token_401(self, client):
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer bad-token"})
        assert response.status_code == 401
