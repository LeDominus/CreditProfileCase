
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from fastapi import HTTPException, status
from src.config.products import PRODUCTS
from src.core.applications import ApplicationRepository
from src.core.conversations import ConversationRepository
from src.core.profile import ProfileRepository
from src.schemas.application_schema import Application
from src.schemas.conversation_schema import Conversation
from src.config.llm_config import PROFILE_FIELDS
from src.schemas.profile_schema import BusinessProfile


def get_product(product_id: int) -> dict | None:
    """Продукт из каталога по id."""
    return next((p for p in PRODUCTS if p["id"] == product_id), None)


def application_response(application: Application) -> dict:
    """Заявка в виде JSON-совместимого словаря."""
    return {
        "id": application.id,
        "profile_id": application.profile_id,
        "product_id": application.product_id,
        "product_name": application.product_name,
        "requested_amount": application.requested_amount,
        "term_months": application.term_months,
        "monthly_payment": application.monthly_payment,
        "total_repayment": application.total_repayment,
        "overpayment": application.overpayment,
        "status": application.status,
        "score": application.score,
        "decision": application.decision,
        "decision_details": application.decision_details,
        "client_data": application.client_data,
        "created_at": application.created_at.isoformat(),
        "updated_at": application.updated_at.isoformat(),
    }


def get_application_or_404(app_rep: ApplicationRepository, application_id: int) -> Application:
    try:
        application = app_rep.get_application(application_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get application: {str(e)}")
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id={application_id} not found",
        )
    return application


def get_owned_application_or_404(
    app_rep: ApplicationRepository,
    profile_rep: ProfileRepository,
    application_id: int,
    user_id: int,
) -> Application:
    """Заявка пользователя; 404 — если не найдена или принадлежит другому (не раскрываем существование)."""
    application = get_application_or_404(app_rep, application_id)
    try:
        profile = profile_rep.get_profile(application.profile_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")
    if profile is None or profile.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with id={application_id} not found",
        )
    return application


def get_profile_or_404(profile_rep: ProfileRepository, profile_id: int) -> BusinessProfile:
    try:
        profile = profile_rep.get_profile(profile_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get profile: {str(e)}",
        )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with id={profile_id} not found",
        )
    return profile

def profile_to_dict(profile: BusinessProfile) -> dict:
    """Профиль в виде словаря полей из PROFILE_FIELDS"""
    return {field: getattr(profile, field) for field in PROFILE_FIELDS}


def get_owned_conversation_or_404(conv_rep: ConversationRepository, conversation_id: int, user_id: int) -> Conversation:
    """Диалог пользователя; 404 — если не найден или принадлежит другому (не раскрываем существование)."""
    try:
        conversation = conv_rep.get_conversation(conversation_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")
    if conversation is None or conversation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with id={conversation_id} not found",
        )
    return conversation


def get_owned_profile_or_404(profile_rep: ProfileRepository, profile_id: int, user_id: int) -> BusinessProfile:
    """Профиль пользователя; 404 — если не найден или принадлежит другому."""
    profile = get_profile_or_404(profile_rep, profile_id)
    if profile.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with id={profile_id} not found",
        )
    return profile

def setup_logging(log_dir: str | Path | None = None) -> Path:
    """Файловое логирование backend: data/logs/backend.log """
    log_path = Path(log_dir if log_dir is not None else os.getenv("LOG_DIR", "data/logs"))
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / "backend.log"
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    for handler in [h for h in root.handlers if isinstance(h, RotatingFileHandler)]:
        handler.close()
        root.removeHandler(handler)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    if not any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
        for h in root.handlers
    ):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)
    return log_file

def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))