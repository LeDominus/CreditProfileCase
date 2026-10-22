"""Тесты реестра компаний по ИНН и пакета данных клиента в заявке."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.config.registry import REGISTRY_ENTRIES
from src.core.registry import get_registry_entry
from src.schemas.profile_schema import ClientDataRequest
from tests.conftest import authorize_client


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URI", f"sqlite:///{tmp_path / 'api_test.db'}")
    from main import app

    with TestClient(app) as test_client:
        authorize_client(test_client)
        yield test_client


REGISTRY_INN = REGISTRY_ENTRIES[0]["inn"]


def build_client_data(**overrides):
    entry = get_registry_entry(REGISTRY_INN)
    data = {
        "credit": {
            "credit_product": "оборотный кредит",
            "credit_sum": 3_000_000,
            "credit_term_months": 12,
            "credit_target": "Закупка сырья",
        },
        "company": {
            "inn": entry["inn"],
            **entry["company"],
            "company_place": "г. Москва, ул. Хлебная, д. 12",
            "taxation_system": "УСН доходы минус расходы",
            "company_members_count": 14,
            "company_phone": "+79991234567",
            "company_email": "info@pekarnya.ru",
        },
        "supervisor": {
            **entry["supervisor"],
            "passport": "4509 123456",
            "passport_issued_by": "ОУФМС России по г. Москве",
            "place_of_birth": "01.01.1980, г. Москва",
            "registration_address": "г. Москва, ул. Хлебная, д. 12",
            "inn_fiz_face": "770112345678",
            "supervisor_phone": "+79991234568",
            "supervisor_email": "director@pekarnya.ru",
            "owners_full_name": ["Смирнова Анна Викторовна"],
            "owners_passport": ["4509 123456"],
        },
        "finance": {
            "revenue": 48_000_000,
            "profit": 6_000_000,
            "current_loans_and_leasing": ["Альфа-Банк, остаток 500000, платёж 60000"],
            "has_debts": False,
        },
        "documents": {
            "supervisor_passport_scan": "passport.pdf",
            "business_type": "ooo",
            "business_doc": ["ustav.pdf", "balance.pdf"],
        },
        "consents": {
            "personal_data_agreement": True,
            "credit_history_agreement": True,
        },
    }
    for section, values in overrides.items():
        data[section].update(values)
    return data


def create_profile(client):
    return client.post(
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


class TestRegistryCore:
    def test_get_registry_entry_found(self):
        entry = get_registry_entry(REGISTRY_INN)
        assert entry is not None
        assert entry["company"]["company_name"] == "ООО «Северная пекарня»"
        assert entry["supervisor"]["full_name"] == "Смирнова Анна Викторовна"

    def test_get_registry_entry_not_found(self):
        assert get_registry_entry("0000000000") is None

    def test_registry_inns_are_unique(self):
        inns = [entry["inn"] for entry in REGISTRY_ENTRIES]
        assert len(inns) == len(set(inns))


class TestRegistryEndpoint:
    def test_get_registry_success(self, client):
        response = client.get(f"/api/registry/{REGISTRY_INN}")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["inn"] == REGISTRY_INN
        assert body["company"]["ogrn"]
        assert body["supervisor"]["full_name"]

    def test_get_registry_not_found(self, client):
        response = client.get("/api/registry/0000000000")
        assert response.status_code == 404


class TestClientDataSchema:
    def test_valid_client_data(self):
        model = ClientDataRequest.model_validate(build_client_data())
        assert model.company.inn == REGISTRY_INN
        assert model.documents.business_type == "ooo"

    def test_invalid_company_phone_rejected(self):
        with pytest.raises(ValidationError):
            ClientDataRequest.model_validate(
                build_client_data(company={"company_phone": "89991234567"})
            )

    def test_invalid_inn_rejected(self):
        with pytest.raises(ValidationError):
            ClientDataRequest.model_validate(build_client_data(company={"inn": "123"}))

    def test_consents_required(self):
        with pytest.raises(ValidationError):
            ClientDataRequest.model_validate(
                build_client_data(consents={"personal_data_agreement": False})
            )

    def test_unknown_credit_product_rejected(self):
        with pytest.raises(ValidationError):
            ClientDataRequest.model_validate(
                build_client_data(credit={"credit_product": "ипотека"})
            )


class TestApplicationClientData:
    def test_create_application_with_client_data(self, client):
        profile_id = create_profile(client)
        response = client.post(
            "/api/applications",
            json={
                "profile_id": profile_id,
                "product_id": 1,
                "requested_amount": 3_000_000,
                "term_months": 12,
                "client_data": build_client_data(),
            },
        )
        assert response.status_code == 201
        application = response.json()["application"]
        assert application["client_data"]["company"]["inn"] == REGISTRY_INN
        assert application["client_data"]["supervisor"]["full_name"]

        stored = client.get(f"/api/applications/{application['id']}").json()["application"]
        assert stored["client_data"]["credit"]["credit_sum"] == 3_000_000

    def test_create_application_without_client_data(self, client):
        profile_id = create_profile(client)
        response = client.post(
            "/api/applications",
            json={
                "profile_id": profile_id,
                "product_id": 1,
                "requested_amount": 3_000_000,
                "term_months": 12,
            },
        )
        assert response.status_code == 201
        assert response.json()["application"]["client_data"] is None

    def test_create_application_with_invalid_client_data(self, client):
        profile_id = create_profile(client)
        response = client.post(
            "/api/applications",
            json={
                "profile_id": profile_id,
                "product_id": 1,
                "requested_amount": 3_000_000,
                "term_months": 12,
                "client_data": build_client_data(company={"inn": "123"}),
            },
        )
class TestRegistryFullProfile:
    """Каждая запись реестра покрывает все разделы пакета данных клиента."""

    @pytest.mark.parametrize("entry", REGISTRY_ENTRIES, ids=lambda item: item["inn"])
    def test_entry_validates_as_client_data(self, entry):
        payload = {
            "credit": {
                "credit_product": "оборотный кредит",
                "credit_sum": 3_000_000,
                "credit_term_months": 12,
                "credit_target": "Пополнение оборотных средств",
            },
            "company": {**entry["company"], "inn": entry["inn"]},
            "supervisor": entry["supervisor"],
            "finance": entry["finance"],
            "documents": {
                "supervisor_passport_scan": "passport.pdf",
                "business_type": "ip" if len(entry["inn"]) == 12 else "ooo",
                "business_doc": ["ustav.pdf"],
            },
            "consents": {
                "personal_data_agreement": True,
                "credit_history_agreement": True,
            },
        }
        model = ClientDataRequest.model_validate(payload)
        assert model.company.inn == entry["inn"]
        assert model.company.company_phone.startswith("+7")
        assert model.supervisor.full_name
        assert model.finance.revenue > 0

