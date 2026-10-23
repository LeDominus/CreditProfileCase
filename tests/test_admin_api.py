"""Тесты рабочего места сотрудника банка: очередь заявок и действия по ролям (п. 2.5)."""

import pytest
from fastapi.testclient import TestClient

from src.schemas.application_schema import (
    ALLOWED_TRANSITIONS,
    STATUS_MANUAL_REVIEW,
    STATUS_NEEDS_INFO,
    STATUS_OFFER_READY,
    STATUS_REJECTED,
)
from tests.conftest import authorize_client


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URI", f"sqlite:///{tmp_path / 'api_test.db'}")
    from main import app

    with TestClient(app) as test_client:
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

# пограничный профиль: балл ~69 — внутри MANUAL_REVIEW_SCORE_RANGE (50, 70)
MID_PROFILE = {
    **STRONG_PROFILE,
    "business_age_months": 12,
    "monthly_revenue": 500_000,
    "monthly_profit": 40_000,
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


def submit_application(client, application_id):
    response = client.post(f"/api/applications/{application_id}/submit")
    assert response.status_code == 200
    return response.json()["application"]


def bank_headers(client, role, username):
    token = client.post(
        "/api/auth/register",
        json={"username": username, "password": "secret123", "role": role},
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def force_status(client, application_id, status):
    """Прямая установка статуса в БД: транзитные статусы конвейера иначе не поймать."""
    app_rep = client.app.state.app_rep
    application = app_rep.get_application(application_id)
    application.status = status
    app_rep.update_application(application)


def manual_review_application(client):
    """Заявка с пограничным профилем (балл ~69): после submit — статус manual_review.

    Триггер интервала 50–70 отдельно покрыт в test_scoring_service.py
    (TestManualReviewTrigger) — здесь это только предусловие действий АРМ.
    """
    profile_id = create_profile(
        client,
        **{
            k: v
            for k, v in MID_PROFILE.items()
            if k not in ("industry", "funding_purpose")
        },
    )
    application = create_application(client, profile_id=profile_id)
    return submit_application(client, application["id"])


# Целевая матрица переходов (ТЗ, пп. 2.4–2.6): тест фиксирует её как спецификацию
EXPECTED_TRANSITIONS = {
    "draft": {"submitted"},
    "submitted": {"data_check"},
    "data_check": {"scoring", "rejected", "needs_info", "manual_review"},
    "scoring": {"approved", "approved_with_changes", "rejected", "needs_info", "manual_review"},
    "needs_info": {"data_check"},
    "manual_review": {"approved", "approved_with_changes", "rejected", "needs_info"},
    "approved": {"offer_ready"},
    "approved_with_changes": {"offer_ready"},
    "offer_ready": {"accepted", "client_declined"},
    "accepted": {"signed"},
    "signed": {"issued"},
    "rejected": set(),
    "issued": set(),
    "client_declined": set(),
}


class TestTransitionMatrix:
    """Матрица переходов фиксируется целиком как спецификация (ТЗ, пп. 2.4–2.6).

    can_transition — тривиальный lookup по ALLOWED_TRANSITIONS, поэтому
    параметризованная проверка всех 196 пар избыточна (DRY).
    """

    def test_matrix_matches_spec(self):
        assert ALLOWED_TRANSITIONS == EXPECTED_TRANSITIONS


class TestAdminListApplications:
    @pytest.mark.parametrize(
        ("role", "username"),
        [("bank_manager", "manager1"), ("bank_analyst", "analyst1")],
    )
    def test_bank_roles_see_all_applications(self, client, role, username):
        application = submit_application(client, create_application(client)["id"])
        headers = bank_headers(client, role, username)
        response = client.get("/api/admin/applications", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert application["id"] in [a["id"] for a in body["applications"]]

    def test_client_role_forbidden_403(self, client):
        assert client.get("/api/admin/applications").status_code == 403

    def test_without_token_401(self, client):
        response = client.get(
            "/api/admin/applications", headers={"Authorization": ""}
        )
        assert response.status_code == 401

    def test_status_filter(self, client):
        submit_application(client, create_application(client)["id"])
        headers = bank_headers(client, "bank_manager", "manager2")
        response = client.get(
            "/api/admin/applications", params={"status": "offer_ready"}, headers=headers
        )
        assert response.status_code == 200
        applications = response.json()["applications"]
        assert applications
        assert all(a["status"] == "offer_ready" for a in applications)

    def test_unknown_status_422(self, client):
        headers = bank_headers(client, "bank_manager", "manager3")
        response = client.get(
            "/api/admin/applications", params={"status": "unknown"}, headers=headers
        )
        assert response.status_code == 422


class TestManagerActions:
    """Действия кредитного менеджера: запрос уточнений и передача аналитику."""

    def test_request_info_moves_to_needs_info(self, client):
        application = manual_review_application(client)
        headers = bank_headers(client, "bank_manager", "manager4")
        response = client.post(
            f"/api/admin/applications/{application['id']}/request-info",
            json={"message": "Подтвердите выручку за последний квартал"},
            headers=headers,
        )
        assert response.status_code == 200
        stored = response.json()["application"]
        assert stored["status"] == STATUS_NEEDS_INFO
        assert stored["decision_details"]["needs_info_reason"] == (
            "Подтвердите выручку за последний квартал"
        )
        history = client.get(f"/api/applications/{application['id']}/history").json()
        assert history["history"][-1]["actor_type"] == "bank_manager"
        assert history["history"][-1]["comment"] == "Подтвердите выручку за последний квартал"

    def test_client_rescores_after_request_info(self, client):
        application = manual_review_application(client)
        headers = bank_headers(client, "bank_manager", "manager5")
        client.post(
            f"/api/admin/applications/{application['id']}/request-info",
            json={"message": "Уточните данные о бизнесе"},
            headers=headers,
        )
        patch = client.patch(
            f"/api/profile/{application['profile_id']}",
            json={
                "business_age_months": 36,
                "monthly_revenue": 800_000,
                "monthly_profit": 150_000,
            },
        )
        assert patch.status_code == 200
        response = client.post(f"/api/applications/{application['id']}/scoring")
        assert response.status_code == 200
        assert response.json()["application"]["status"] == STATUS_OFFER_READY

    def test_request_info_wrong_status_409(self, client):
        application = create_application(client)  # черновик
        headers = bank_headers(client, "bank_manager", "manager6")
        response = client.post(
            f"/api/admin/applications/{application['id']}/request-info",
            json={"message": "Нужны уточнения"},
            headers=headers,
        )
        assert response.status_code == 409

    def test_request_info_by_analyst_403(self, client):
        application = manual_review_application(client)
        headers = bank_headers(client, "bank_analyst", "analyst2")
        response = client.post(
            f"/api/admin/applications/{application['id']}/request-info",
            json={"message": "Нужны уточнения"},
            headers=headers,
        )
        assert response.status_code == 403

    def test_request_info_short_message_422(self, client):
        application = manual_review_application(client)
        headers = bank_headers(client, "bank_manager", "manager7")
        response = client.post(
            f"/api/admin/applications/{application['id']}/request-info",
            json={"message": "ок"},
            headers=headers,
        )
        assert response.status_code == 422

    def test_assign_analyst_moves_to_manual_review(self, client):
        application = create_application(client)
        force_status(client, application["id"], "data_check")
        headers = bank_headers(client, "bank_manager", "manager8")
        response = client.post(
            f"/api/admin/applications/{application['id']}/assign-analyst",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["application"]["status"] == STATUS_MANUAL_REVIEW

    def test_assign_analyst_wrong_status_409(self, client):
        application = create_application(client)  # черновик
        headers = bank_headers(client, "bank_manager", "manager9")
        response = client.post(
            f"/api/admin/applications/{application['id']}/assign-analyst",
            headers=headers,
        )
        assert response.status_code == 409

    def test_assign_analyst_by_analyst_403(self, client):
        application = create_application(client)
        headers = bank_headers(client, "bank_analyst", "analyst3")
        response = client.post(
            f"/api/admin/applications/{application['id']}/assign-analyst",
            headers=headers,
        )
        assert response.status_code == 403


class TestAnalystDecision:
    """Решение кредитного аналитика по заявке в ручной экспертизе (с причиной)."""

    def test_rejected_with_reason(self, client):
        application = manual_review_application(client)
        headers = bank_headers(client, "bank_analyst", "analyst4")
        response = client.post(
            f"/api/admin/applications/{application['id']}/decision",
            json={"decision": "rejected", "reason": "Долговая нагрузка выше политики банка"},
            headers=headers,
        )
        assert response.status_code == 200
        stored = response.json()["application"]
        assert stored["status"] == STATUS_REJECTED
        assert stored["decision"] == "rejected"
        assert stored["decision_details"]["analyst_decision"]["reason"] == (
            "Долговая нагрузка выше политики банка"
        )
        history = client.get(f"/api/applications/{application['id']}/history").json()
        assert history["history"][-1]["actor_type"] == "bank_analyst"
        assert history["history"][-1]["comment"] == "Долговая нагрузка выше политики банка"

    def test_approved_moves_to_offer_ready(self, client):
        application = manual_review_application(client)
        headers = bank_headers(client, "bank_analyst", "analyst5")
        response = client.post(
            f"/api/admin/applications/{application['id']}/decision",
            json={"decision": "approved", "reason": "Профиль подтверждён документами"},
            headers=headers,
        )
        assert response.status_code == 200
        stored = response.json()["application"]
        assert stored["status"] == STATUS_OFFER_READY
        history = client.get(f"/api/applications/{application['id']}/history").json()
        assert history["history"][-2]["to_status"] == "approved"
        assert history["history"][-1]["to_status"] == STATUS_OFFER_READY

    def test_decision_by_manager_403(self, client):
        application = manual_review_application(client)
        headers = bank_headers(client, "bank_manager", "manager10")
        response = client.post(
            f"/api/admin/applications/{application['id']}/decision",
            json={"decision": "approved", "reason": "Всё в порядке"},
            headers=headers,
        )
        assert response.status_code == 403

    def test_decision_wrong_status_409(self, client):
        application = create_application(client)  # черновик
        headers = bank_headers(client, "bank_analyst", "analyst6")
        response = client.post(
            f"/api/admin/applications/{application['id']}/decision",
            json={"decision": "approved", "reason": "Всё в порядке"},
            headers=headers,
        )
        assert response.status_code == 409

    def test_decision_invalid_value_422(self, client):
        application = manual_review_application(client)
        headers = bank_headers(client, "bank_analyst", "analyst7")
        response = client.post(
            f"/api/admin/applications/{application['id']}/decision",
            json={"decision": "needs_info", "reason": "Всё в порядке"},
            headers=headers,
        )
        assert response.status_code == 422

    def test_decision_short_reason_422(self, client):
        application = manual_review_application(client)
        headers = bank_headers(client, "bank_analyst", "analyst8")
        response = client.post(
            f"/api/admin/applications/{application['id']}/decision",
            json={"decision": "approved", "reason": "ок"},
            headers=headers,
        )
        assert response.status_code == 422
