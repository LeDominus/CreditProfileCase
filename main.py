import logging
import uvicorn
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, HTTPException, status
from src.core.llm.extract_pipeline import extract_content
from src.config.products import PRODUCTS
from src.core.llm.LLMApi import LLMApi
from src.core.applications import ApplicationRepository
from src.core.profile import ProfileRepository
from src.core.recommendations import recommend_products
from src.core.scoring_service import (
    ApplicationNotFoundError,
    InvalidApplicationStatusError,
    ProfileNotFoundError,
    ProductNotFoundError,
    ScoringError,
    process_application_scoring,
)
from src.core.calc_payment import calculate_annuity_payment
from src.DI import (
    load_LLM,
    load_application_repository,
    load_conversation_repository,
    load_profile_repository,
)
from src.core.conversations import ConversationRepository
from src.database.database import DatabaseConnector
from src.schemas.llm_schema import ContractExtraction
from src.schemas.application_schema import (
    STATUS_APPROVED,
    STATUS_APPROVED_WITH_CHANGES,
    STATUS_ISSUED,
    STATUS_SUBMITTED,
    Application,
    ApplicationConfirmRequest,
    ApplicationCreateRequest,
)
from src.schemas.conversation_schema import (
    Conversation,
    ConversationCreateMessage,
    ConversationCreateRequest,
    Message,
)
from src.schemas.product_schemas import RecommendationRequest
from src.schemas.profile_schema import (
    BusinessProfile,
    ProfileCreateRequest,
    ProfileRequest,
)
from src.config.sql_queries import (
    CREATE_APPLICATIONS_TABLE,
    CREATE_BUSINESS_PROFILES_TABLE,
    CREATE_CONVERSATIONS_TABLE,
    CREATE_MESSAGES_TABLE,
)
from src.utils import (
    profile_to_dict, get_product,
    application_response,
    get_application_or_404,
    get_profile_or_404,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

@asynccontextmanager
async def lifespan(app):
    print("Запуск приложения...")
    try:
        app.state.dbConn = DatabaseConnector()
    except Exception as e:
        raise RuntimeError(f"[app] Ошибка при инициализации DatabaseConnector: {e}") from e

    try:
        with app.state.dbConn as conn:
            conn.load_data(CREATE_CONVERSATIONS_TABLE)
            conn.load_data(CREATE_MESSAGES_TABLE)
            conn.load_data(CREATE_BUSINESS_PROFILES_TABLE)
            conn.load_data(CREATE_APPLICATIONS_TABLE)
    except Exception as e:
        raise RuntimeError(f"[app] Ошибка при создании таблиц: {e}") from e

    try:
        app.state.conv_rep = ConversationRepository(dbConn=app.state.dbConn)
    except Exception as e:
        raise RuntimeError(f"[app] Ошибка при инициализации ConversationRepository: {e}") from e
    
    try:
        app.state.profile_rep = ProfileRepository(dbConn=app.state.dbConn)
    except Exception as e:
        raise RuntimeError(f"[app] Ошибка при инициализации ProfileRepository: {e}") from e

    try:
        app.state.app_rep = ApplicationRepository(dbConn=app.state.dbConn)
    except Exception as e:
        raise RuntimeError(f"[app] Ошибка при инициализации ApplicationRepository: {e}") from e
    
    try:
        app.state.llmAPI = LLMApi()
    except Exception as e:
        raise RuntimeError

    print("Приложение успешно запущено!")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreateRequest,
    conv_rep: ConversationRepository = Depends(load_conversation_repository)
) -> dict:
    try:
        new_conversation = Conversation(state=payload.state)
        conversation_id = conv_rep.create_conversation(new_conversation)
        return {"status": "success", "id": conversation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")
    
@app.post("/api/conversations/{conversation_id}/messages", status_code=status.HTTP_201_CREATED)
def create_conversation_message(
    conversation_id: int,
    payload: ConversationCreateMessage,
    conv_rep: ConversationRepository = Depends(load_conversation_repository),
    profile_rep: ProfileRepository = Depends(load_profile_repository),
    llm: LLMApi = Depends(load_LLM),
) -> ContractExtraction:
    """LLM-конвейер обработки сообщения"""
    try:
        if conv_rep.get_conversation(conversation_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation with id={conversation_id} not found"
            )

        new_message = Message(
            conversation_id=conversation_id,
            role=payload.role,
            content=payload.content
        )
        message_id = conv_rep.send_conversation_message(new_message)

        return extract_content(
            conv_rep=conv_rep,
            profile_rep=profile_rep,
            llm=llm,
            payload=payload,
            conversation_id=conversation_id,
            message_id=message_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")
    
@app.get("/api/conversations")
def list_conversations(
    conv_rep: ConversationRepository = Depends(load_conversation_repository),
) -> dict:
    """Список диалогов, свежие сверху (для восстановления истории в UI)."""
    try:
        conversations = conv_rep.get_conversations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")
    return {
        "status": "success",
        "conversations": [
            {
                "id": c.id,
                "state": c.state,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in conversations
        ],
    }

@app.get("/api/conversations/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: int,
    conv_rep: ConversationRepository = Depends(load_conversation_repository),
) -> dict:
    """Все сообщения диалога в хронологическом порядке."""
    try:
        if conv_rep.get_conversation(conversation_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation with id={conversation_id} not found"
            )
        messages = conv_rep.get_conversation_messages(conversation_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")
    return {
        "status": "success",
        "conversation_id": conversation_id,
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in messages
        ],
    }

@app.post("/api/recommendations")
def load_catalog(payload: RecommendationRequest) -> dict:
    recommendations = recommend_products(payload.model_dump())
    return {"status": "success", "recommendations": recommendations}
    
@app.post("/api/profile", status_code=status.HTTP_201_CREATED, response_model=BusinessProfile)
def create_profile(
    payload: ProfileCreateRequest,
    profile_rep: ProfileRepository = Depends(load_profile_repository)
) -> BusinessProfile:
    try:
        new_profile = BusinessProfile(
            business_name=payload.business_name,
            industry=payload.industry,
            funding_purpose=payload.funding_purpose,
            requested_amount=payload.requested_amount,
            business_age_months=payload.business_age_months,
            monthly_revenue=payload.monthly_revenue,
            monthly_profit=payload.monthly_profit,
            preferred_term_months=payload.preferred_term_months,
            max_monthly_payment=payload.max_monthly_payment,
        )
        profile_id = profile_rep.create_profile(new_profile)
        return profile_rep.get_profile(profile_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create profile: {str(e)}")
    
@app.patch("/api/profile/{profile_id}", response_model=BusinessProfile)
def update_profile(
    profile_id: int,
    payload: ProfileRequest,
    profile_rep: ProfileRepository = Depends(load_profile_repository)
) -> BusinessProfile:
    current = get_profile_or_404(profile_rep, profile_id)
    try:
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return current

        updated = replace(current, **changes)
        updated.updated_at = datetime.now(timezone.utc)

        if profile_rep.update_profile(updated) is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update profile with id={profile_id}"
            )
        return profile_rep.get_profile(profile_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")
    
@app.get("/api/profile/{profile_id}", response_model=BusinessProfile)
def get_profile(
    profile_id: int,
    profile_rep: ProfileRepository = Depends(load_profile_repository)
) -> BusinessProfile:
    return get_profile_or_404(profile_rep, profile_id)

@app.post("/api/profile/{profile_id}/payment")
def calc_payment_for_profile(
    profile_id: int,
    profile_rep: ProfileRepository = Depends(load_profile_repository)
) -> dict:
    """Расчёт аннуитетного платежа по профилю + подбор продукта"""
    profile = get_profile_or_404(profile_rep, profile_id)

    profile_dict = profile_to_dict(profile)
    if (
        profile_dict.get("requested_amount") is None
        or profile_dict.get("preferred_term_months") is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Profile must have requested_amount and preferred_term_months to calculate payment"
        )

    recommendations = recommend_products(profile_dict)
    if not recommendations:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No suitable products for this profile"
        )
    best = recommendations[0]
    #TODO: подставить нужную data schema\ pydantic схему вместо сырого return {}
    return {
        "status": "success",
        "profile_id": profile_id,
        "product": {"id": best["id"], "name": best["name"], "rate": best["rate"]},
        "requested_amount": profile_dict["requested_amount"],
        "term_months": profile_dict["preferred_term_months"],
        "monthly_payment": best["monthly_payment"],
        "total_repayment": best["total_repayment"],
        "overpayment": best["overpayment"],
    }

@app.post("/api/applications", status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreateRequest,
    profile_rep: ProfileRepository = Depends(load_profile_repository),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Создание заявки: валидация профиля/продукта + аннуитетный расчёт"""
    profile = get_profile_or_404(profile_rep, payload.profile_id)

    product = get_product(payload.product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id={payload.product_id} not found",
        )

    if not product["min_amount"] <= payload.requested_amount <= product["max_amount"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Requested amount must be between {product['min_amount']} and "
                f"{product['max_amount']} for product '{product['name']}'"
            ),
        )
    if not product["min_term"] <= payload.term_months <= product["max_term"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Term must be between {product['min_term']} and {product['max_term']} "
                f"months for product '{product['name']}'"
            ),
        )
    if (
        profile.business_age_months is not None
        and profile.business_age_months < product["min_age"]
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Business age {profile.business_age_months} months is below the minimum "
                f"{product['min_age']} months for product '{product['name']}'"
            ),
        )

    monthly_payment = calculate_annuity_payment(
        float(payload.requested_amount), float(product["rate"]), payload.term_months
    )
    total_repayment = round(monthly_payment * payload.term_months, 4)
    overpayment = round(total_repayment - payload.requested_amount, 4)

    application = Application(
        profile_id=payload.profile_id,
        product_id=payload.product_id,
        product_name=product["name"],
        requested_amount=float(payload.requested_amount),
        term_months=payload.term_months,
        monthly_payment=monthly_payment,
        total_repayment=total_repayment,
        overpayment=overpayment,
        status=STATUS_SUBMITTED,
    )
    try:
        application_id = app_rep.create_application(application)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create application: {str(e)}")

    stored = app_rep.get_application(application_id)
    return {"status": "success", "application": application_response(stored)}


@app.post("/api/applications/{application_id}/scoring")
def run_application_scoring(
    application_id: int,
    profile_rep: ProfileRepository = Depends(load_profile_repository),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Скоринг заявки: submitted/needs_info -> scoring -> решение."""
    try:
        application, scoring = process_application_scoring(application_id, app_rep, profile_rep)
    except ApplicationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ProfileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ProductNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidApplicationStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ScoringError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "status": "success",
        "application": application_response(application),
        "scoring": scoring,
    }


@app.post("/api/applications/{application_id}/confirm")
def confirm_application(
    application_id: int,
    payload: ApplicationConfirmRequest,
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Финальное подтверждение клиента: approved* -> issued (выдача смоделирована)."""
    application = get_application_or_404(app_rep, application_id)
    if not payload.confirmed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Confirmation must be explicit (confirmed=true)",
        )
    if application.status not in (STATUS_APPROVED, STATUS_APPROVED_WITH_CHANGES):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only approved applications can be confirmed "
                f"(current: '{application.status}')"
            ),
        )

    application.status = STATUS_ISSUED
    application.updated_at = datetime.now(timezone.utc)
    try:
        if app_rep.update_application(application) is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update application with id={application_id}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update application: {str(e)}")

    stored = app_rep.get_application(application_id)
    return {"status": "success", "application": application_response(stored)}


@app.get("/api/applications/{application_id}")
def get_application(
    application_id: int,
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Заявка по id со статусом и результатом скоринга."""
    application = get_application_or_404(app_rep, application_id)
    return {"status": "success", "application": application_response(application)}


@app.get("/api/profile/{profile_id}/applications")
def get_profile_applications(
    profile_id: int,
    profile_rep: ProfileRepository = Depends(load_profile_repository),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Все заявки профиля, новые сверху."""
    get_profile_or_404(profile_rep, profile_id)
    try:
        applications = app_rep.get_applications_by_profile(profile_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list applications: {str(e)}")
    return {
        "status": "success",
        "profile_id": profile_id,
        "applications": [application_response(a) for a in applications],
    }


@app.get("/api/products")
def get_products() -> list[dict]:
    """Каталог кредитных продуктов"""
    return PRODUCTS




if __name__ == "__main__":
    uvicorn.run(host = "127.0.0.1", app = app, port=5555)