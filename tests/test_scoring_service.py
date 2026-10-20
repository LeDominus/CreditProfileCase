"""Юнит-тесты сервиса скоринга: process_application_scoring без HTTP-слоя."""

import pytest

from src.core.scoring_service import (
    ApplicationNotFoundError,
    InvalidApplicationStatusError,
    ProfileNotFoundError,
    process_application_scoring,
)
from src.schemas.application_schema import (
    STATUS_APPROVED,
    STATUS_ISSUED,
    STATUS_NEEDS_INFO,
    STATUS_SUBMITTED,
    Application,
)
from src.schemas.profile_schema import BusinessProfile


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


def make_application(profile_id, status=STATUS_SUBMITTED):
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
    )


@pytest.fixture()
def profile_id(profile_repo):
    return profile_repo.create_profile(make_profile())


@pytest.fixture()
def application_id(app_repo, profile_id):
    return app_repo.create_application(make_application(profile_id))


class TestHappyPath:
    def test_returns_updated_application_and_scoring(self, app_repo, profile_repo, application_id):
        application, scoring = process_application_scoring(
            application_id, app_repo, profile_repo
        )
        assert application.id == application_id
        assert application.status == STATUS_APPROVED
        assert application.score == scoring["score"]
        assert application.decision == scoring["decision"]
        assert application.decision_details == scoring

    def test_persists_result(self, app_repo, profile_repo, application_id):
        _, scoring = process_application_scoring(application_id, app_repo, profile_repo)
        stored = app_repo.get_application(application_id)
        assert stored.status == STATUS_APPROVED
        assert stored.score == scoring["score"]
        assert stored.decision_details == scoring

    def test_needs_info_can_be_rescored(self, app_repo, profile_repo, temp_db):
        # профиль без финансовых полей -> needs_info
        pid = profile_repo.create_profile(
            make_profile(monthly_revenue=None, monthly_profit=None)
        )
        aid = app_repo.create_application(make_application(pid))
        _, first = process_application_scoring(aid, app_repo, profile_repo)
        assert first["decision"] == STATUS_NEEDS_INFO

        # уточнили данные -> повторный скоринг даёт решение
        profile = profile_repo.get_profile(pid)
        profile.monthly_revenue = 800_000
        profile.monthly_profit = 150_000
        profile_repo.update_profile(profile)
        application, second = process_application_scoring(aid, app_repo, profile_repo)
        assert application.status == STATUS_APPROVED
        assert second["decision"] == STATUS_APPROVED


class TestErrors:
    def test_missing_application(self, app_repo, profile_repo):
        with pytest.raises(ApplicationNotFoundError):
            process_application_scoring(999, app_repo, profile_repo)

    def test_invalid_status(self, app_repo, profile_repo, application_id):
        application = app_repo.get_application(application_id)
        application.status = STATUS_ISSUED
        app_repo.update_application(application)
        with pytest.raises(InvalidApplicationStatusError):
            process_application_scoring(application_id, app_repo, profile_repo)

    def test_missing_profile(self, app_repo, profile_repo):
        aid = app_repo.create_application(make_application(profile_id=999))
        with pytest.raises(ProfileNotFoundError):
            process_application_scoring(aid, app_repo, profile_repo)
