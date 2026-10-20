"""Интеграционные тесты конвейера заявок: создание -> скоринг -> подтверждение."""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import ChatStubLLM, authorize_client


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URI", f"sqlite:///{tmp_path / 'api_test.db'}")
    from main import app

    with TestClient(app) as test_client:
        test_client.app.state.llmAPI = ChatStubLLM()
        authorize_client(test_client)
        yield test_client


STRONG_PROFILE = {
    "industry": "IT",
    "funding_purpose": "Развитие бизнеса",
    "business_age_months": 36,
    "monthly_revenue": 800_000,
    "monthly_profit": 150_000,
    "preferred_term_months": 24,
    "requested_amount": 1_500_000,
}


def create_profile(client, **overrides):
    payload = dict(STRONG_PROFILE)
    payload.update(overrides)
    return client.post("/api/profile", json=payload).json()["id"]


def create_application(client, profile_id=None, product_id=1, amount=1_500_000, term=24):
    if profile_id is None:
        profile_id = create_profile(client)
    response = client.post(
        "/api/applications",
        json={
            "profile_id": profile_id,
            "product_id": product_id,
            "requested_amount": amount,
            "term_months": term,
        },
    )
    assert response.status_code == 201
    return response.json()["application"]


class TestCreateApplication:
    def test_create_submitted_application(self, client):
        profile_id = create_profile(client)
        application = create_application(client, profile_id=profile_id)
        assert application["status"] == "submitted"
        assert application["profile_id"] == profile_id
        assert application["product_name"] == "Оборотный капитал"
        assert application["monthly_payment"] > 0
        assert application["total_repayment"] == pytest.approx(
            application["monthly_payment"] * application["term_months"], rel=1e-3
        )
        assert application["overpayment"] == pytest.approx(
            application["total_repayment"] - application["requested_amount"], rel=1e-3
        )
        assert application["score"] is None

    def test_create_missing_profile_404(self, client):
        response = client.post(
            "/api/applications",
            json={
                "profile_id": 999,
                "product_id": 1,
                "requested_amount": 1_000_000,
                "term_months": 12,
            },
        )
        assert response.status_code == 404

    def test_create_missing_product_404(self, client):
        profile_id = create_profile(client)
        response = client.post(
            "/api/applications",
            json={
                "profile_id": profile_id,
                "product_id": 999,
                "requested_amount": 1_000_000,
                "term_months": 12,
            },
        )
        assert response.status_code == 404

    def test_create_amount_out_of_range_422(self, client):
        profile_id = create_profile(client)
        response = client.post(
            "/api/applications",
            json={
                "profile_id": profile_id,
                "product_id": 1,
                "requested_amount": 100_000,  # минимум продукта — 300 000
                "term_months": 12,
            },
        )
        assert response.status_code == 422

    def test_create_term_out_of_range_422(self, client):
        profile_id = create_profile(client)
        response = client.post(
            "/api/applications",
            json={
                "profile_id": profile_id,
                "product_id": 1,
                "requested_amount": 1_000_000,
                "term_months": 60,  # максимум продукта — 36 мес
            },
        )
        assert response.status_code == 422


class TestScoringEndpoint:
    def test_full_path_to_approval(self, client):
        application = create_application(client)
        application_id = application["id"]

        response = client.post(f"/api/applications/{application_id}/scoring")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"

        scoring = body["scoring"]
        assert scoring["decision"] == "approved"
        assert scoring["score"] >= 70
        assert len(scoring["factors"]) == 4

        stored = body["application"]
        assert stored["status"] == "approved"
        assert stored["score"] == scoring["score"]
        assert stored["decision"] == "approved"
        assert stored["decision_details"]["explanation"]

    def test_scoring_needs_info_then_rescore(self, client):
        # профиль без финансовых данных -> needs_info
        profile_id = create_profile(client, monthly_revenue=None, monthly_profit=None)
        application = create_application(client, profile_id=profile_id)
        response = client.post(f"/api/applications/{application['id']}/scoring")
        assert response.status_code == 200
        assert response.json()["application"]["status"] == "needs_info"
        assert response.json()["scoring"]["missing_fields"]

        # клиент уточнил данные -> повторный скоринг даёт решение
        patch = client.patch(
            f"/api/profile/{profile_id}",
            json={
                "monthly_revenue": 800_000,
                "monthly_profit": 150_000,
                "business_age_months": 36,
            },
        )
        assert patch.status_code == 200
        response = client.post(f"/api/applications/{application['id']}/scoring")
        assert response.status_code == 200
        assert response.json()["application"]["status"] == "approved"

    def test_scoring_rejected_for_weak_profile(self, client):
        profile_id = create_profile(
            client, monthly_revenue=200_000, monthly_profit=10_000, business_age_months=6
        )
        application = create_application(client, profile_id=profile_id)
        response = client.post(f"/api/applications/{application['id']}/scoring")
        assert response.status_code == 200
        assert response.json()["application"]["status"] == "rejected"

    def test_double_scoring_409(self, client):
        application = create_application(client)
        assert client.post(f"/api/applications/{application['id']}/scoring").status_code == 200
        response = client.post(f"/api/applications/{application['id']}/scoring")
        assert response.status_code == 409

    def test_scoring_missing_application_404(self, client):
        assert client.post("/api/applications/999/scoring").status_code == 404


class TestConfirmEndpoint:
    def test_confirm_approved_application_issues(self, client):
        application = create_application(client)
        application_id = application["id"]
        assert client.post(f"/api/applications/{application_id}/scoring").status_code == 200

        response = client.post(
            f"/api/applications/{application_id}/confirm", json={"confirmed": True}
        )
        assert response.status_code == 200
        assert response.json()["application"]["status"] == "issued"

    def test_confirm_not_explicit_422(self, client):
        application = create_application(client)
        response = client.post(
            f"/api/applications/{application['id']}/confirm", json={"confirmed": False}
        )
        assert response.status_code == 422

    def test_confirm_before_scoring_409(self, client):
        application = create_application(client)
        response = client.post(
            f"/api/applications/{application['id']}/confirm", json={"confirmed": True}
        )
        assert response.status_code == 409

    def test_confirm_rejected_application_409(self, client):
        profile_id = create_profile(
            client, monthly_revenue=200_000, monthly_profit=10_000, business_age_months=6
        )
        application = create_application(client, profile_id=profile_id)
        assert client.post(f"/api/applications/{application['id']}/scoring").status_code == 200
        response = client.post(
            f"/api/applications/{application['id']}/confirm", json={"confirmed": True}
        )
        assert response.status_code == 409

    def test_confirm_missing_application_404(self, client):
        response = client.post("/api/applications/999/confirm", json={"confirmed": True})
        assert response.status_code == 404


class TestGetApplications:
    def test_get_application_by_id(self, client):
        application = create_application(client)
        response = client.get(f"/api/applications/{application['id']}")
        assert response.status_code == 200
        assert response.json()["application"]["id"] == application["id"]

    def test_get_missing_application_404(self, client):
        assert client.get("/api/applications/999").status_code == 404

    def test_list_profile_applications(self, client):
        profile_id = create_profile(client)
        first = create_application(client, profile_id=profile_id)
        second = create_application(client, profile_id=profile_id, amount=2_000_000)

        response = client.get(f"/api/profile/{profile_id}/applications")
        assert response.status_code == 200
        body = response.json()
        assert body["profile_id"] == profile_id
        assert [a["id"] for a in body["applications"]] == [second["id"], first["id"]]

    def test_list_applications_missing_profile_404(self, client):
        assert client.get("/api/profile/999/applications").status_code == 404

    def test_create_business_age_below_minimum_422(self, client):
        profile_id = create_profile(client, business_age_months=3)
        response = client.post(
            "/api/applications",
            json={
                "profile_id": profile_id,
                "product_id": 1,
                "requested_amount": 1_000_000,
                "term_months": 12,
            },
        )
        assert response.status_code == 422