"""Юнит-тесты конвейера обработки заявки: process_application_scoring без HTTP-слоя."""

import pytest

from src.core.scoring_service import (
    ApplicationNotFoundError,
    InvalidApplicationStatusError,
    ProfileNotFoundError,
    process_application_scoring,
)
from src.schemas.application_schema import (
    STATUS_APPROVED,
    STATUS_DATA_CHECK,
    STATUS_ISSUED,
    STATUS_MANUAL_REVIEW,
    STATUS_NEEDS_INFO,
    STATUS_OFFER_READY,
    STATUS_REJECTED,
    STATUS_SCORING,
    STATUS_SUBMITTED,
    Application,
)
from src.schemas.profile_schema import BusinessProfile
from src.schemas.scoring_schema import ScoringResult


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
        assert application.status == STATUS_OFFER_READY
        assert application.score == scoring["score"]
        assert application.decision == scoring["decision"]
        assert application.decision_details == scoring

    def test_persists_result(self, app_repo, profile_repo, application_id):
        _, scoring = process_application_scoring(application_id, app_repo, profile_repo)
        stored = app_repo.get_application(application_id)
        assert stored.status == STATUS_OFFER_READY
        assert stored.score == scoring["score"]
        assert stored.decision_details == scoring

    def test_writes_status_history(self, app_repo, profile_repo, application_id):
        process_application_scoring(application_id, app_repo, profile_repo)
        history = app_repo.get_status_history(application_id)
        assert [(h["from_status"], h["to_status"]) for h in history] == [
            (STATUS_SUBMITTED, STATUS_DATA_CHECK),
            (STATUS_DATA_CHECK, STATUS_SCORING),
            (STATUS_SCORING, STATUS_APPROVED),
            (STATUS_APPROVED, STATUS_OFFER_READY),
        ]
        assert all(h["actor_type"] == "system" for h in history)
        assert all(h["actor_id"] is None for h in history)

    def test_needs_info_can_be_rescored(self, app_repo, profile_repo, temp_db):
        # профиль без финансовых полей -> needs_info
        pid = profile_repo.create_profile(
            make_profile(monthly_revenue=None, monthly_profit=None)
        )
        aid = app_repo.create_application(make_application(pid))
        _, first = process_application_scoring(aid, app_repo, profile_repo)
        assert first["decision"] == STATUS_NEEDS_INFO
        assert app_repo.get_application(aid).status == STATUS_NEEDS_INFO

        # уточнили данные -> повторная обработка даёт решение и предложение
        profile = profile_repo.get_profile(pid)
        profile.monthly_revenue = 800_000
        profile.monthly_profit = 150_000
        profile_repo.update_profile(profile)
        application, second = process_application_scoring(aid, app_repo, profile_repo)
        assert application.status == STATUS_OFFER_READY
        assert second["decision"] == STATUS_APPROVED


class TestManualReviewTrigger:
    """Триггер ручной проверки: интервал-заглушка MANUAL_REVIEW_SCORE_RANGE (до п. 2.5)."""

    @staticmethod
    def _fix_score(monkeypatch, score):
        monkeypatch.setattr(
            "src.core.scoring_service.MANUAL_REVIEW_SCORE_RANGE", (50.0, 70.0)
        )
        monkeypatch.setattr(
            "src.core.scoring_service.score_application",
            lambda *args, **kwargs: ScoringResult(
                score=score, decision=STATUS_APPROVED, explanation="stub"
            ),
        )

    def test_border_score_goes_to_manual_review(
        self, app_repo, profile_repo, application_id, monkeypatch
    ):
        self._fix_score(monkeypatch, 60.0)
        application, scoring = process_application_scoring(
            application_id, app_repo, profile_repo
        )
        assert application.status == STATUS_MANUAL_REVIEW
        assert scoring["score"] == 60.0
        history = app_repo.get_status_history(application_id)
        assert history[-1]["to_status"] == STATUS_MANUAL_REVIEW
        assert "ручную проверку" in history[-1]["comment"]

    def test_high_score_skips_manual_review(
        self, app_repo, profile_repo, application_id, monkeypatch
    ):
        self._fix_score(monkeypatch, 80.0)
        application, _ = process_application_scoring(application_id, app_repo, profile_repo)
        assert application.status == STATUS_OFFER_READY


class TestAlternativesOnRejection:
    """п. 2.7: при отказе в decision_details попадают альтернативные продукты."""

    @staticmethod
    def _weak_profile_id(profile_repo):
        # слабый профиль: балл ~34 < CONDITIONS_SCORE (50) -> отказ
        return profile_repo.create_profile(
            make_profile(
                monthly_revenue=200_000, monthly_profit=10_000, business_age_months=6
            )
        )

    def test_rejected_application_gets_alternatives(self, app_repo, profile_repo):
        pid = self._weak_profile_id(profile_repo)
        aid = app_repo.create_application(make_application(pid))
        application, scoring = process_application_scoring(aid, app_repo, profile_repo)
        assert scoring["decision"] == STATUS_REJECTED
        alternatives = scoring["alternatives"]
        assert alternatives
        # исходный продукт (id=1) в альтернативы не попадает
        assert all(alt["id"] != 1 for alt in alternatives)
        for alt in alternatives:
            assert alt["amount"] > 0
            assert alt["monthly_payment"] > 0
        # альтернативы сохраняются вместе с decision_details
        stored = app_repo.get_application(aid)
        assert stored.decision_details["alternatives"] == alternatives

    def test_approved_application_has_no_alternatives(
        self, app_repo, profile_repo, application_id
    ):
        application, scoring = process_application_scoring(
            application_id, app_repo, profile_repo
        )
        assert scoring["decision"] == STATUS_APPROVED
        assert "alternatives" not in scoring


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