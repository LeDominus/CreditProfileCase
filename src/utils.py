
from fastapi import HTTPException, status
from src.config.products import PRODUCTS
from src.core.applications import ApplicationRepository
from src.core.profile import ProfileRepository
from src.schemas.application_schema import Application
from src.config.llm_config import PROFILE_FIELDS
from src.schemas.profile_schema import BusinessProfile


FALLBACK_REPLY = (
    "Сообщение принято. Ассистент временно недоступен — "
    "продолжу помогать, как только связь восстановится."
)

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