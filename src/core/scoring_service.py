"""Сервис скоринга заявки: банковская логика конвейера без HTTP-слоя.

Эндпоинт в main.py только вызывает process_application_scoring и маппит
доменные исключения в HTTP-коды.
"""

from datetime import datetime, timezone

from src.core.applications import ApplicationRepository
from src.core.profile import ProfileRepository
from src.core.scoring import score_application
from src.schemas.application_schema import (
    STATUS_NEEDS_INFO,
    STATUS_SCORING,
    STATUS_SUBMITTED,
    Application,
    can_transition,
)
from src.utils import get_product, profile_to_dict


class ScoringError(Exception):
    """Базовая ошибка конвейера скоринга заявки."""


class ApplicationNotFoundError(ScoringError):
    """Заявка не найдена."""


class InvalidApplicationStatusError(ScoringError):
    """Недопустимый статус заявки или переход статусов."""


class ProfileNotFoundError(ScoringError):
    """Профиль, на который ссылается заявка, не найден."""


class ProductNotFoundError(ScoringError):
    """Продукт, на который ссылается заявка, не найден."""


class ScoringRepositoryError(ScoringError):
    """Сбой доступа к БД при скоринге заявки."""


def process_application_scoring(
    application_id: int,
    app_rep: ApplicationRepository,
    profile_rep: ProfileRepository,
) -> tuple[Application, dict]:
    """Скоринг заявки: submitted/needs_info -> scoring -> решение.

    Проверяет допустимость скоринга по статусу, считает балл, проводит заявку
    через статусную модель (с проверкой переходов) и фиксирует результат
    в БД. Возвращает кортеж (заявка из БД после обновления, результат
    скоринга в виде словаря).
    """
    application = _get_application(app_rep, application_id)
    if application.status not in (STATUS_SUBMITTED, STATUS_NEEDS_INFO):
        raise InvalidApplicationStatusError(
            "Scoring is allowed only for applications in status "
            f"'{STATUS_SUBMITTED}' or '{STATUS_NEEDS_INFO}' "
            f"(current: '{application.status}')"
        )

    profile = _get_profile(profile_rep, application.profile_id)
    product = get_product(application.product_id)
    if product is None:
        raise ProductNotFoundError(
            f"Product with id={application.product_id} not found"
        )

    result = score_application(
        profile_to_dict(profile),
        product,
        application.requested_amount,
        application.term_months,
        application.monthly_payment,
    )

    for new_status in (STATUS_SCORING, result.decision):
        if not can_transition(application.status, new_status):
            raise InvalidApplicationStatusError(
                f"Transition '{application.status}' -> '{new_status}' is not allowed"
            )
        application.status = new_status
        application.updated_at = datetime.now(timezone.utc)
        if new_status == result.decision:
            application.score = result.score
            application.decision = result.decision
            application.decision_details = result.to_dict()
        _update_application(app_rep, application)

    stored = _get_application(app_rep, application_id)
    return stored, result.to_dict()


def _get_application(
    app_rep: ApplicationRepository, application_id: int
) -> Application:
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


def _update_application(app_rep: ApplicationRepository, application: Application) -> None:
    try:
        if app_rep.update_application(application) is None:
            raise ScoringRepositoryError(
                f"Failed to update application with id={application.id}"
            )
    except ScoringError:
        raise
    except Exception as e:
        raise ScoringRepositoryError(f"Failed to update application: {e}") from e
