"""Интеграционные тесты HTTP API: TestClient + временная SQLite + стаб LLM."""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import ChatStubLLM


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URI", f"sqlite:///{tmp_path / 'api_test.db'}")
    from main import app

    with TestClient(app) as test_client:
        # подменяем LLM на стаб: конвейер сообщений не должен ходить в сеть
        test_client.app.state.llmAPI = ChatStubLLM()
        yield test_client


class TestHealth:
    def test_health(self, client):
        assert client.get("/health").json() == {"status": "ok"}


class TestConversations:
    def test_create_conversation(self, client):
        response = client.post("/api/conversations", json={"state": "new"})
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "success"
        assert isinstance(body["id"], int)

    def test_send_message(self, client):
        conversation_id = client.post("/api/conversations", json={}).json()["id"]
        response = client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"role": "user", "content": "Нужен кредит"},
        )
        assert response.status_code == 201
        assert response.json()["conversation_id"] == conversation_id

    def test_send_message_to_missing_conversation(self, client):
        response = client.post(
            "/api/conversations/999/messages",
            json={"role": "user", "content": "hi"},
        )
        assert response.status_code == 404


class TestConversationsHistory:
    """GET /api/conversations и GET /api/conversations/{id}/messages —
    восстановление истории диалогов после перезагрузки страницы."""

    def test_list_conversations_empty(self, client):
        response = client.get("/api/conversations")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["conversations"] == []

    def test_list_conversations_after_create(self, client):
        first = client.post("/api/conversations", json={}).json()["id"]
        second = client.post("/api/conversations", json={}).json()["id"]
        response = client.get("/api/conversations")
        assert response.status_code == 200
        conversations = response.json()["conversations"]
        ids = [c["id"] for c in conversations]
        assert ids == [second, first]  # свежие сверху
        assert all("created_at" in c and "updated_at" in c for c in conversations)

    def test_get_messages_of_missing_conversation_404(self, client):
        assert client.get("/api/conversations/999/messages").status_code == 404

    def test_get_messages_returns_dialog_history(self, client):
        conversation_id = client.post("/api/conversations", json={}).json()["id"]
        client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"role": "user", "content": "Нужен кредит"},
        )
        response = client.get(f"/api/conversations/{conversation_id}/messages")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["conversation_id"] == conversation_id
        roles = [m["role"] for m in body["messages"]]
        contents = [m["content"] for m in body["messages"]]
        assert roles == ["user", "assistant"]
        assert contents[0] == "Нужен кредит"
        assert contents[1] == "Расскажите подробнее о вашем бизнесе."


class TestMessagesPipeline:
    """LLM-конвейер POST /api/conversations/{id}/messages."""

    def test_message_without_profile_gets_reply(self, client):
        conversation_id = client.post("/api/conversations", json={}).json()["id"]
        response = client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"role": "user", "content": "Привет"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["reply"] == "Расскажите подробнее о вашем бизнесе."
        assert body["profile"] is None
        assert body["profile_updates"] == {}
        assert body["recommendations"] == []
        assert isinstance(body["assistant_message_id"], int)

    def test_pipeline_extracts_updates_and_recommends(self, client):
        conversation_id = client.post("/api/conversations", json={}).json()["id"]
        profile_id = client.post(
            "/api/profile",
            json={
                "industry": "общепит",
                "funding_purpose": "Пополнение оборотных средств",
                "requested_amount": 1_500_000,
                "business_age_months": 24,
                "preferred_term_months": 24,
            },
        ).json()["id"]

        response = client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={
                "role": "user",
                "content": "Нужно 2 миллиона на 18 месяцев",
                "profile_id": profile_id,
            },
        )
        assert response.status_code == 201
        body = response.json()

        # LLM извлекла поля из сообщения
        assert body["profile_updates"] == {
            "requested_amount": 2_000_000.0,
            "preferred_term_months": 18,
        }
        # профиль обновлён в БД (проверяем отдельным GET)
        fetched = client.get(f"/api/profile/{profile_id}").json()
        assert fetched["requested_amount"] == 2_000_000
        assert fetched["preferred_term_months"] == 18
        assert fetched["industry"] == "общепит"  # прежние поля не затёрты

        # рекомендации посчитаны: 2 млн / 18 мес подходят 3 продукта из 4
        assert len(body["recommendations"]) == 3
        first = body["recommendations"][0]
        assert first["purpose_match"] is True  # «Оборотный капитал» по цели
        assert first["monthly_payment"] > 0
        assert first["overpayment"] > 0

    def test_message_with_missing_profile_404(self, client):
        conversation_id = client.post("/api/conversations", json={}).json()["id"]
        response = client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"role": "user", "content": "hi", "profile_id": 999},
        )
        assert response.status_code == 404

    def test_role_defaults_to_user(self, client):
        conversation_id = client.post("/api/conversations", json={}).json()["id"]
        response = client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "Без поля role"},
        )
        assert response.status_code == 201


class TestRecommendationsEndpoint:
    def test_post_recommendations(self, client):
        response = client.post(
            "/api/recommendations",
            json={
                "funding_purpose": "Пополнение оборотных средств",
                "requested_amount": 1_500_000,
                "preferred_term_months": 24,
                "business_age_months": 24,
            },
        )
        assert response.status_code == 200
        recs = response.json()["recommendations"]
        assert recs
        assert all("monthly_payment" in rec for rec in recs)
        assert all("overpayment" in rec for rec in recs)

    def test_recommendations_ignore_unknown_fields(self, client):
        response = client.post(
            "/api/recommendations",
            json={"requested_amount": 1_500_000, "hack": 1},
        )
        assert response.status_code == 200


class TestProductsEndpoint:
    def test_get_products(self, client):
        response = client.get("/api/products")
        assert response.status_code == 200
        products = response.json()
        assert any(product["id"] == 1 for product in products)
        assert all("rate" in product for product in products)


class TestProfile:
    def test_create_get_update_flow(self, client):
        payload = {
            "business_name": "ООО Ромашка",
            "industry": "общепит",
            "funding_purpose": "Пополнение оборотных средств",
            "requested_amount": 1_500_000,
            "business_age_months": 24,
            "preferred_term_months": 24,
        }
        created = client.post("/api/profile", json=payload)
        assert created.status_code == 201
        profile = created.json()
        profile_id = profile["id"]
        assert profile["industry"] == "общепит"

        fetched = client.get(f"/api/profile/{profile_id}")
        assert fetched.status_code == 200
        assert fetched.json()["requested_amount"] == 1_500_000

        patched = client.patch(
            f"/api/profile/{profile_id}", json={"requested_amount": 3_000_000}
        )
        assert patched.status_code == 200
        assert patched.json()["requested_amount"] == 3_000_000
        # непереданные поля не затёрты
        assert patched.json()["industry"] == "общепит"

    def test_patch_empty_body_returns_current(self, client):
        profile_id = client.post(
            "/api/profile",
            json={
                "industry": "IT",
                "funding_purpose": "Развитие",
                "business_age_months": 12,
                "preferred_term_months": 24,
            },
        ).json()["id"]
        response = client.patch(f"/api/profile/{profile_id}", json={})
        assert response.status_code == 200
        assert response.json()["industry"] == "IT"

    def test_patch_missing_profile_404(self, client):
        assert client.patch("/api/profile/999", json={"industry": "IT"}).status_code == 404

    def test_get_missing_profile_404(self, client):
        assert client.get("/api/profile/999").status_code == 404

    def test_unknown_field_rejected_422(self, client):
        response = client.post(
            "/api/profile",
            json={
                "industry": "IT",
                "funding_purpose": "Развитие",
                "business_age_months": 12,
                "preferred_term_months": 24,
                "hack": 1,
            },
        )
        assert response.status_code == 422

    def test_create_with_placeholder_required_fields(self, client):
        """Контракт с фронтендом: профиль создаётся при первом сообщении диалога,
        когда industry/funding_purpose/business_age_months ещё не извлечены —
        фронтенд шлёт заглушки для NOT NULL строк, стаж не шлёт вовсе."""
        response = client.post(
            "/api/profile",
            json={
                "industry": "Не указано",
                "funding_purpose": "Не указано",
                "requested_amount": 1_500_000,
                "preferred_term_months": 24,
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["industry"] == "Не указано"
        assert body["requested_amount"] == 1_500_000
        assert body["business_age_months"] is None


class TestProfilePaymentEndpoint:
    """POST /api/profile/{id}/payment — аннуитетный расчёт по профилю."""

    def _create_profile(self, client, **overrides):
        payload = {
            "industry": "IT",
            "funding_purpose": "Развитие бизнеса",
            "business_age_months": 24,
            "preferred_term_months": 24,
            "requested_amount": 1_500_000,
        }
        payload.update(overrides)
        return client.post("/api/profile", json=payload).json()["id"]

    def test_payment_for_profile(self, client):
        profile_id = self._create_profile(client)
        response = client.post(f"/api/profile/{profile_id}/payment")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["profile_id"] == profile_id
        assert isinstance(body["product"]["id"], int)
        assert body["product"]["rate"] > 0
        assert body["monthly_payment"] > 0
        assert body["total_repayment"] == pytest.approx(
            body["monthly_payment"] * body["term_months"], rel=1e-3
        )
        assert body["overpayment"] == pytest.approx(
            body["total_repayment"] - body["requested_amount"], rel=1e-3
        )

    def test_payment_missing_profile_404(self, client):
        assert client.post("/api/profile/999/payment").status_code == 404

    def test_payment_without_amount_422(self, client):
        profile_id = self._create_profile(client, requested_amount=None)
        response = client.post(f"/api/profile/{profile_id}/payment")
        assert response.status_code == 422
        assert "requested_amount" in response.json()["detail"]

    def test_payment_no_suitable_products_422(self, client):
        profile_id = self._create_profile(client, requested_amount=100_000_000)
        response = client.post(f"/api/profile/{profile_id}/payment")
        assert response.status_code == 422
        assert "No suitable products" in response.json()["detail"]