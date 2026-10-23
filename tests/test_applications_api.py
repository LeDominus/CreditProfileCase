"""Интеграционные тесты жизненного цикла заявки: draft -> submit -> решение -> отклик -> подписание."""

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


def submit_application(client, application_id):
    response = client.post(f"/api/applications/{application_id}/submit")
    assert response.status_code == 200
    return response.json()


def other_user_headers(client, username="intruder"):
    token = client.post(
        "/api/auth/register", json={"username": username, "password": "secret123"}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


class TestCreateApplication:
    def test_create_draft_application(self, client):
        profile_id = create_profile(client)
        application = create_application(client, profile_id=profile_id)
        assert application["status"] == "draft"
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


class TestSubmitEndpoint:
    def test_submit_runs_pipeline_to_offer_ready(self, client):
        application = create_application(client)
        body = submit_application(client, application["id"])

        scoring = body["scoring"]
        assert scoring["decision"] == "approved"
        assert scoring["score"] >= 70
        assert len(scoring["factors"]) == 4

        stored = body["application"]
        assert stored["status"] == "offer_ready"
        assert stored["score"] == scoring["score"]
        assert stored["decision"] == "approved"
        assert stored["decision_details"]["explanation"]

    def test_submit_needs_info(self, client):
        profile_id = create_profile(client, monthly_revenue=None, monthly_profit=None)
        application = create_application(client, profile_id=profile_id)
        body = submit_application(client, application["id"])
        assert body["application"]["status"] == "needs_info"
        assert body["scoring"]["missing_fields"]

    def test_submit_rejected_for_weak_profile(self, client):
        profile_id = create_profile(
            client, monthly_revenue=200_000, monthly_profit=10_000, business_age_months=6
        )
        application = create_application(client, profile_id=profile_id)
        body = submit_application(client, application["id"])
        assert body["application"]["status"] == "rejected"
        # п. 2.7: при отказе клиент получает альтернативные продукты
        alternatives = body["application"]["decision_details"]["alternatives"]
        assert alternatives
        assert all(alt["id"] != 1 for alt in alternatives)
        assert body["scoring"]["alternatives"] == alternatives

    def test_submit_twice_409(self, client):
        application = create_application(client)
        submit_application(client, application["id"])
        response = client.post(f"/api/applications/{application['id']}/submit")
        assert response.status_code == 409

    def test_submit_missing_application_404(self, client):
        assert client.post("/api/applications/999/submit").status_code == 404


class TestScoringEndpoint:
    """Повторная обработка после needs_info (уточнение данных профиля)."""

    def test_rescore_after_needs_info(self, client):
        profile_id = create_profile(client, monthly_revenue=None, monthly_profit=None)
        application = create_application(client, profile_id=profile_id)
        body = submit_application(client, application["id"])
        assert body["application"]["status"] == "needs_info"

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
        assert response.json()["application"]["status"] == "offer_ready"

    def test_scoring_draft_409(self, client):
        application = create_application(client)
        assert client.post(f"/api/applications/{application['id']}/scoring").status_code == 409

    def test_double_scoring_409(self, client):
        application = create_application(client)
        submit_application(client, application["id"])
        response = client.post(f"/api/applications/{application['id']}/scoring")
        assert response.status_code == 409

    def test_scoring_missing_application_404(self, client):
        assert client.post("/api/applications/999/scoring").status_code == 404


class TestUpdateDraftEndpoint:
    def test_patch_draft_recalculates_payments(self, client):
        application = create_application(client)
        response = client.patch(
            f"/api/applications/{application['id']}",
            json={"requested_amount": 2_000_000, "term_months": 36},
        )
        assert response.status_code == 200
        stored = response.json()["application"]
        assert stored["status"] == "draft"
        assert stored["requested_amount"] == 2_000_000
        assert stored["term_months"] == 36
        assert stored["monthly_payment"] > 0
        assert stored["total_repayment"] == pytest.approx(
            stored["monthly_payment"] * 36, rel=1e-3
        )

    def test_patch_non_draft_409(self, client):
        application = create_application(client)
        submit_application(client, application["id"])
        response = client.patch(
            f"/api/applications/{application['id']}",
            json={"requested_amount": 2_000_000},
        )
        assert response.status_code == 409

    def test_patch_amount_out_of_range_422(self, client):
        application = create_application(client)
        response = client.patch(
            f"/api/applications/{application['id']}",
            json={"requested_amount": 100_000},
        )
        assert response.status_code == 422

    def test_patch_missing_application_404(self, client):
        response = client.patch(
            "/api/applications/999", json={"requested_amount": 2_000_000}
        )
        assert response.status_code == 404


class TestOfferResponseEndpoint:
    def test_accept_offer(self, client):
        application = create_application(client)
        submit_application(client, application["id"])
        response = client.post(
            f"/api/applications/{application['id']}/offer-response",
            json={"accept": True},
        )
        assert response.status_code == 200
        assert response.json()["application"]["status"] == "accepted"

    def test_decline_offer(self, client):
        application = create_application(client)
        submit_application(client, application["id"])
        response = client.post(
            f"/api/applications/{application['id']}/offer-response",
            json={"accept": False, "decline_reason": "Дорогой платёж"},
        )
        assert response.status_code == 200
        assert response.json()["application"]["status"] == "client_declined"

        history = client.get(f"/api/applications/{application['id']}/history").json()
        assert history["history"][-1]["comment"] == "Причина отказа: Дорогой платёж"

    def test_offer_response_wrong_status_409(self, client):
        application = create_application(client)
        response = client.post(
            f"/api/applications/{application['id']}/offer-response",
            json={"accept": True},
        )
        assert response.status_code == 409

    def test_offer_response_missing_application_404(self, client):
        response = client.post(
            "/api/applications/999/offer-response", json={"accept": True}
        )
        assert response.status_code == 404


class TestSignEndpoint:
    def test_sign_issues_application(self, client):
        application = create_application(client)
        submit_application(client, application["id"])
        client.post(
            f"/api/applications/{application['id']}/offer-response", json={"accept": True}
        )
        response = client.post(f"/api/applications/{application['id']}/sign")
        assert response.status_code == 200
        assert response.json()["application"]["status"] == "issued"

    def test_sign_not_accepted_409(self, client):
        application = create_application(client)
        submit_application(client, application["id"])
        response = client.post(f"/api/applications/{application['id']}/sign")
        assert response.status_code == 409

    def test_sign_missing_application_404(self, client):
        assert client.post("/api/applications/999/sign").status_code == 404


class TestHistoryEndpoint:
    def test_history_full_lifecycle(self, client):
        application = create_application(client)
        application_id = application["id"]
        submit_application(client, application_id)
        client.post(f"/api/applications/{application_id}/offer-response", json={"accept": True})
        client.post(f"/api/applications/{application_id}/sign")

        response = client.get(f"/api/applications/{application_id}/history")
        assert response.status_code == 200
        history = response.json()["history"]
        assert [(h["from_status"], h["to_status"]) for h in history] == [
            ("draft", "submitted"),
            ("submitted", "data_check"),
            ("data_check", "scoring"),
            ("scoring", "approved"),
            ("approved", "offer_ready"),
            ("offer_ready", "accepted"),
            ("accepted", "signed"),
            ("signed", "issued"),
        ]
        actors = [h["actor_type"] for h in history]
        assert actors == ["client", "system", "system", "system", "system", "client", "client", "system"]

    def test_history_missing_application_404(self, client):
        assert client.get("/api/applications/999/history").status_code == 404


class TestOwnership:
    """Чужая заявка/профиль — 404 (не раскрываем существование)."""

    def test_foreign_application_404(self, client):
        application = create_application(client)
        application_id = application["id"]
        headers = other_user_headers(client)

        assert client.get(f"/api/applications/{application_id}", headers=headers).status_code == 404
        assert client.post(f"/api/applications/{application_id}/submit", headers=headers).status_code == 404
        assert client.post(f"/api/applications/{application_id}/scoring", headers=headers).status_code == 404
        assert (
            client.patch(
                f"/api/applications/{application_id}",
                json={"requested_amount": 2_000_000},
                headers=headers,
            ).status_code
            == 404
        )
        assert (
            client.post(
                f"/api/applications/{application_id}/offer-response",
                json={"accept": True},
                headers=headers,
            ).status_code
            == 404
        )
        assert client.post(f"/api/applications/{application_id}/sign", headers=headers).status_code == 404
        assert client.get(f"/api/applications/{application_id}/history", headers=headers).status_code == 404

    def test_foreign_profile_applications_404(self, client):
        profile_id = create_profile(client)
        headers = other_user_headers(client)
        assert (
            client.get(f"/api/profile/{profile_id}/applications", headers=headers).status_code
            == 404
        )

    def test_create_application_for_foreign_profile_404(self, client):
        headers = other_user_headers(client)
        foreign_profile_id = client.post(
            "/api/profile", json=STRONG_PROFILE, headers=headers
        ).json()["id"]
        response = client.post(
            "/api/applications",
            json={
                "profile_id": foreign_profile_id,
                "product_id": 1,
                "requested_amount": 1_000_000,
                "term_months": 12,
            },
        )
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


class TestExplainEndpoint:
    """п. 2.8: POST /api/applications/{id}/explain — ИИ-объяснение решения."""

    @staticmethod
    def rejected_application(client):
        profile_id = create_profile(
            client, monthly_revenue=200_000, monthly_profit=10_000, business_age_months=6
        )
        application = create_application(client, profile_id=profile_id)
        body = submit_application(client, application["id"])
        assert body["application"]["status"] == "rejected"
        return application

    def test_explain_rejected_application(self, client):
        application = self.rejected_application(client)
        response = client.post(f"/api/applications/{application['id']}/explain")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["application_id"] == application["id"]
        assert body["audience"] == "client"
        assert body["source"] == "llm"
        assert body["explanation"] == "Расскажите подробнее о вашем бизнесе."

    def test_explain_analyst_audience(self, client):
        application = self.rejected_application(client)
        response = client.post(
            f"/api/applications/{application['id']}/explain",
            json={"audience": "analyst"},
        )
        assert response.status_code == 200
        assert response.json()["audience"] == "analyst"

    def test_explain_without_decision_409(self, client):
        application = create_application(client)  # черновик — решения ещё нет
        response = client.post(f"/api/applications/{application['id']}/explain")
        assert response.status_code == 409

    def test_explain_invalid_audience_422(self, client):
        application = self.rejected_application(client)
        response = client.post(
            f"/api/applications/{application['id']}/explain",
            json={"audience": "manager"},
        )
        assert response.status_code == 422

    def test_explain_missing_application_404(self, client):
        assert client.post("/api/applications/999/explain").status_code == 404

    def test_explain_foreign_application_404(self, client):
        application = self.rejected_application(client)
        headers = other_user_headers(client)
        response = client.post(
            f"/api/applications/{application['id']}/explain", headers=headers
        )
        assert response.status_code == 404

    def test_explain_llm_failure_returns_fallback(self, client):
        application = self.rejected_application(client)

        class FailingLLM(ChatStubLLM):
            def complete(self, context, temperature=None, max_tokens=None, reasoning_effort=None, model=None):
                raise RuntimeError("LLM unavailable")

        client.app.state.llmAPI = FailingLLM()
        response = client.post(f"/api/applications/{application['id']}/explain")
        assert response.status_code == 200
        body = response.json()
        assert body["source"] == "fallback"
        assert "Балл" in body["explanation"]
class TestMyApplications:
    """GET /api/me/applications — все заявки пользователя по всем его профилям."""

    def test_requires_auth_401(self, client):
        response = client.get("/api/me/applications", headers={"Authorization": ""})
        assert response.status_code == 401

    def test_returns_only_own_applications(self, client):
        own = create_application(client)
        foreign_headers = other_user_headers(client)
        foreign_profile = client.post(
            "/api/profile", json=dict(STRONG_PROFILE), headers=foreign_headers
        ).json()["id"]
        client.post(
            "/api/applications",
            json={
                "profile_id": foreign_profile,
                "product_id": 1,
                "requested_amount": 1_500_000,
                "term_months": 24,
            },
            headers=foreign_headers,
        )
        response = client.get("/api/me/applications")
        assert response.status_code == 200
        body = response.json()
        ids = [app["id"] for app in body["applications"]]
        assert own["id"] in ids
        assert foreign_profile not in [app["profile_id"] for app in body["applications"]]

    def test_applications_across_profiles(self, client):
        profile_one = create_profile(client)
        profile_two = create_profile(client)
        first = create_application(client, profile_id=profile_one)
        second = create_application(client, profile_id=profile_two)
        response = client.get("/api/me/applications")
        assert response.status_code == 200
        ids = [app["id"] for app in response.json()["applications"]]
        assert first["id"] in ids and second["id"] in ids

    def test_newest_first(self, client):
        first = create_application(client)
        second = create_application(client)
        response = client.get("/api/me/applications")
        ids = [app["id"] for app in response.json()["applications"]]
        assert ids.index(second["id"]) < ids.index(first["id"])

    def test_status_reflects_bank_decision(self, client):
        application = create_application(client)
        submit_application(client, application["id"])
        response = client.get("/api/me/applications")
        apps = {app["id"]: app for app in response.json()["applications"]}
        assert apps[application["id"]]["status"] != "draft"
        assert apps[application["id"]]["score"] is not None


class TestMyProfile:
    """GET /api/me/profile — последний профиль пользователя (восстановление сессии)."""

    def test_requires_auth_401(self, client):
        response = client.get("/api/me/profile", headers={"Authorization": ""})
        assert response.status_code == 401

    def test_not_found_without_profiles(self, client):
        assert client.get("/api/me/profile").status_code == 404

    def test_returns_latest_profile(self, client):
        first = create_profile(client)
        second = create_profile(client)
        response = client.get("/api/me/profile")
        assert response.status_code == 200
        assert response.json()["id"] == second
        assert response.json()["id"] != first

    def test_foreign_profiles_isolated(self, client):
        create_profile(client)
        foreign_headers = other_user_headers(client)
        assert client.get("/api/me/profile", headers=foreign_headers).status_code == 404
