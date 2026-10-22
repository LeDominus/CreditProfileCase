"""Тесты стоп-факторов на этапе data_check: ликвидация и текущая просрочка (п. 2.6)."""

import pytest
from fastapi.testclient import TestClient

from src.config.registry import REGISTRY_ENTRIES
from src.core.scoring_service import process_application_scoring
from src.core.stop_factors import (
    STOP_FACTOR_DEBTS,
    STOP_FACTOR_LIQUIDATION,
    find_stop_factors,
)
from src.schemas.application_schema import (
    STATUS_DATA_CHECK,
    STATUS_OFFER_READY,
    STATUS_REJECTED,
    STATUS_SUBMITTED,
    Application,
)
from src.schemas.profile_schema import BusinessProfile
from tests.conftest import authorize_client
from tests.test_registry import build_client_data


LIQUIDATION_INN = next(e["inn"] for e in REGISTRY_ENTRIES if e.get("liquidation"))
ACTIVE_INN = next(e["inn"] for e in REGISTRY_ENTRIES if not e.get("liquidation"))


def client_data(inn=ACTIVE_INN, has_debts=False):
    return {"company": {"inn": inn}, "finance": {"has_debts": has_debts}}


@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URI", f"sqlite:///{tmp_path / 'api_test.db'}")
    from main import app

    with TestClient(app) as test_client:
        authorize_client(test_client)
        yield test_client


def make_profile(**overrides):
    fields = dict(
        business_name="ООО «Ромашка»",
        industry="IT",
        funding_purpose="Развитие бизнеса",
        requested_amount=1_500_000,
        business_age_months=36,
        monthly_revenue=800_000,
        monthly_profit=150_000,
        preferred_term_months=24,
        max_monthly_payment=None,
    )
    fields.update(overrides)
    return BusinessProfile(**fields)


def make_application(profile_id, client_data_payload=None, status=STATUS_SUBMITTED):
    return Application(
        profile_id=profile_id,
        product_id=1,
        product_name="Оборотный капитал",
        requested_amount=1_500_000,
        term_months=24,
        monthly_payment=75_540.07,
        total_repayment=1_812_961.68,
        overpayment=312_961.68,
        status=status,
        client_data=client_data_payload,
    )


class TestFindStopFactors:
    def test_no_client_data(self):
        assert find_stop_factors(None) == []
        assert find_stop_factors({}) == []

    def test_clean_client_data(self):
        assert find_stop_factors(client_data()) == []

    def test_debts(self):
        factors = find_stop_factors(client_data(has_debts=True))
        assert [f["code"] for f in factors] == [STOP_FACTOR_DEBTS]
        assert factors[0]["label"]

    def test_liquidation(self):
        factors = find_stop_factors(client_data(inn=LIQUIDATION_INN))
        assert [f["code"] for f in factors] == [STOP_FACTOR_LIQUIDATION]

    def test_both_factors(self):
        factors = find_stop_factors(client_data(inn=LIQUIDATION_INN, has_debts=True))
        assert [f["code"] for f in factors] == [
            STOP_FACTOR_LIQUIDATION,
            STOP_FACTOR_DEBTS,
        ]

    def test_unknown_inn_is_not_a_stop_factor(self):
        assert find_stop_factors(client_data(inn="0000000000")) == []


class TestStopFactorsInPipeline:
    @pytest.fixture()
    def profile_id(self, profile_repo):
        return profile_repo.create_profile(make_profile())

    def _submit(self, app_repo, profile_id, client_data_payload):
        return app_repo.create_application(
            make_application(profile_id, client_data_payload)
        )

    def test_debts_reject_before_scoring(self, app_repo, profile_repo, profile_id):
        aid = self._submit(app_repo, profile_id, client_data(has_debts=True))
        application, details = process_application_scoring(aid, app_repo, profile_repo)
        assert application.status == STATUS_REJECTED
        assert application.decision == STATUS_REJECTED
        assert [f["code"] for f in details["stop_factors"]] == [STOP_FACTOR_DEBTS]
        assert "стоп-факторы" in details["explanation"]
        assert "factors" not in details  # скоринг не выполнялся
        history = app_repo.get_status_history(aid)
        assert [(h["from_status"], h["to_status"]) for h in history] == [
            (STATUS_SUBMITTED, STATUS_DATA_CHECK),
            (STATUS_DATA_CHECK, STATUS_REJECTED),
        ]

    def test_liquidation_rejects_before_scoring(self, app_repo, profile_repo, profile_id):
        aid = self._submit(app_repo, profile_id, client_data(inn=LIQUIDATION_INN))
        application, details = process_application_scoring(aid, app_repo, profile_repo)
        assert application.status == STATUS_REJECTED
        assert [f["code"] for f in details["stop_factors"]] == [STOP_FACTOR_LIQUIDATION]

    def test_clean_application_passes_data_check(self, app_repo, profile_repo, profile_id):
        aid = self._submit(app_repo, profile_id, client_data())
        application, _ = process_application_scoring(aid, app_repo, profile_repo)
        assert application.status == STATUS_OFFER_READY


class TestStopFactorsApi:
    def _submitted_application(self, api_client, **client_data_overrides):
        profile_id = api_client.post(
            "/api/profile",
            json={
                "industry": "Производство",
                "funding_purpose": "Пополнение оборотных средств",
                "business_age_months": 60,
                "monthly_revenue": 4_000_000,
                "monthly_profit": 500_000,
                "preferred_term_months": 12,
                "requested_amount": 3_000_000,
            },
        ).json()["id"]
        response = api_client.post(
            "/api/applications",
            json={
                "profile_id": profile_id,
                "product_id": 1,
                "requested_amount": 3_000_000,
                "term_months": 12,
                "client_data": build_client_data(**client_data_overrides),
            },
        )
        assert response.status_code == 201
        application = response.json()["application"]
        body = api_client.post(f"/api/applications/{application['id']}/submit").json()
        return body["application"]

    def test_submit_with_debts_rejected(self, api_client):
        application = self._submitted_application(
            api_client, finance={"has_debts": True}
        )
        assert application["status"] == STATUS_REJECTED
        assert application["decision_details"]["stop_factors"]

    def test_submit_liquidation_rejected(self, api_client):
        application = self._submitted_application(
            api_client, company={"inn": LIQUIDATION_INN}
        )
        assert application["status"] == STATUS_REJECTED
        codes = [f["code"] for f in application["decision_details"]["stop_factors"]]
        assert codes == [STOP_FACTOR_LIQUIDATION]