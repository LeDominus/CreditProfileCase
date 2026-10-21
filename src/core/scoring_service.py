from src.config.scoring_config import MANUAL_REVIEW_SCORE_RANGE
from src.core.applications import (
    ACTOR_SYSTEM,
    ApplicationRepository,
    transition_application,
)
from src.core.profile import ProfileRepository
from src.core.scoring import score_application
from src.schemas.application_schema import (
    STATUS_APPROVED,
    STATUS_APPROVED_WITH_CHANGES,
    STATUS_DATA_CHECK,
    STATUS_MANUAL_REVIEW,
    STATUS_NEEDS_INFO,
    STATUS_OFFER_READY,
    STATUS_SCORING,
    STATUS_SUBMITTED,
    Application,
)
from src.utils import get_product, profile_to_dict
from src.exceptions import *


PIPELINE_ENTRY_STATUSES = (STATUS_SUBMITTED, STATUS_NEEDS_INFO)


def process_application_scoring(
    application_id: int,
    app_rep: ApplicationRepository,
    profile_rep: ProfileRepository,
) -> tuple[Application, dict]:
    """Конвейер обработки заявки.

    submitted|needs_info -> data_check -> scoring -> решение -> offer_ready.
    Все смены статуса идут через transition_application (единая точка)
    с записью в application_status_history.

    Этап data_check до п. 2.6 — мгновенный проход (заглушка).
    """
    application = _get_application(app_rep, application_id)
    if application.status not in PIPELINE_ENTRY_STATUSES:
        raise InvalidApplicationStatusError(
            "Processing is allowed only for applications in status "
            f"'{STATUS_SUBMITTED}' or '{STATUS_NEEDS_INFO}' "
            f"(current: '{application.status}')"
        )

    profile = _get_profile(profile_rep, application.profile_id)
    product = get_product(application.product_id)
    if product is None:
        raise ProductNotFoundError(
            f"Product with id={application.product_id} not found"
        )

    # Этап 1: проверка полноты данных (до п. 2.6 — мгновенный проход)
    application = _transition(
        app_rep, application, STATUS_DATA_CHECK,
        comment="Проверка данных пройдена",
    )

    # Этап 2: скоринг
    application = _transition(app_rep, application, STATUS_SCORING)
    result = score_application(
        profile_to_dict(profile),
        product,
        application.requested_amount,
        application.term_months,
        application.monthly_payment,
    )

    # Пограничный балл — ручная проверка (триггер-заглушка до п. 2.5)
    if _in_manual_review_range(result.score):
        application = _transition(
            app_rep, application, STATUS_MANUAL_REVIEW,
            comment=(
                f"Балл {result.score:g} из 100 — в пограничном интервале, "
                "заявка передана на ручную проверку"
            ),
        )
        return application, result.to_dict()

    # Этап 3: решение (score/decision/decision_details сохраняются вместе со статусом)
    application.score = result.score
    application.decision = result.decision
    application.decision_details = result.to_dict()
    application = _transition(
        app_rep, application, result.decision,
        comment=result.to_dict().get("explanation"),
    )

    # Этап 4: одобрение -> предложение готово к отклику клиента
    if result.decision in (STATUS_APPROVED, STATUS_APPROVED_WITH_CHANGES):
        application = _transition(app_rep, application, STATUS_OFFER_READY)

    return application, result.to_dict()


def _in_manual_review_range(score: float | None) -> bool:
    """Балл в пограничном интервале ручной проверки.

    MANUAL_REVIEW_SCORE_RANGE — заглушка до п. 2.5: None выключает триггер.
    """
    if MANUAL_REVIEW_SCORE_RANGE is None or score is None:
        return False
    low, high = MANUAL_REVIEW_SCORE_RANGE
    return low <= score < high


def _transition(
    app_rep: ApplicationRepository,
    application: Application,
    target_status: str,
    comment: str | None = None,
) -> Application:
    """Смена статуса через единую точку; сбои БД -> ScoringRepositoryError."""
    try:
        return transition_application(
            application, target_status, ACTOR_SYSTEM, None, app_rep, comment=comment
        )
    except ScoringError:
        raise
    except Exception as e:
        raise ScoringRepositoryError(
            f"Failed to transition application to '{target_status}': {e}"
        ) from e


def _get_application(app_rep: ApplicationRepository, application_id: int) -> Application:
    try:
        application = app_rep.get_application(application_id)
    except Exception as e:
        raise ScoringRepositoryError(f"Failed to get application: {e}") from e
    if application is None:
        raise ApplicationNotFoundError(
            f"Application with id={application_id} not found"
        )
    return application


def _get_profile(profile_rep: ProfileRepository, profile_id: int):
    try:
        profile = profile_rep.get_profile(profile_id)
    except Exception as e:
        raise ScoringRepositoryError(f"Failed to get profile: {e}") from e
    if profile is None:
        raise ProfileNotFoundError(f"Profile with id={profile_id} not found")
    return profile