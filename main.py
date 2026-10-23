import logging
import os
import uvicorn
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, HTTPException, Query, status
from src.core.llm.extract_pipeline import extract_content
from src.core.llm.explain_pipeline import explain_application_decision
from src.config.products import PRODUCTS
from src.core.llm.LLMApi import LLMApi
from src.core.applications import (
    ApplicationRepository,
    transition_application,
)
from src.core.auth.auth import (
    AuthRepository,
    InvalidCredentialsError,
    InvalidRoleError,
    UsernameTakenError,
)
from src.core.auth.auth_service_methods import (
    login_user,
    register_user,
    user_response
)
from src.core.auth.dependencies import get_current_user, require_role
from src.core.profile import ProfileRepository
from src.core.recommendations import recommend_products
from src.core.registry import get_registry_entry
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
    load_auth_repository,
    load_conversation_repository,
    load_profile_repository,
)
from src.core.conversations import ConversationRepository
from src.database.database import DatabaseConnector
from src.database.migrations import apply_migrations
from src.schemas.llm_schema import ContractExtraction
from src.schemas.application_schema import (
    APPLICATION_STATUSES,
    STATUS_ACCEPTED,
    STATUS_APPROVED,
    STATUS_APPROVED_WITH_CHANGES,
    STATUS_CLIENT_DECLINED,
    STATUS_DRAFT,
    STATUS_ISSUED,
    STATUS_MANUAL_REVIEW,
    STATUS_NEEDS_INFO,
    STATUS_OFFER_READY,
    STATUS_SIGNED,
    STATUS_SUBMITTED,
    AdminDecisionRequest,
    AdminRequestInfoRequest,
    Application,
    ApplicationCreateRequest,
    ApplicationExplainRequest,
    ApplicationOfferResponseRequest,
    ApplicationUpdateRequest,
)
from src.schemas.auth_schema import AuthLoginRequest, AuthRegisterRequest, User
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
    CREATE_APPLICATION_STATUS_HISTORY_TABLE,
    CREATE_AUTH_TOKENS_TABLE,
    CREATE_BUSINESS_PROFILES_TABLE,
    CREATE_CONVERSATIONS_TABLE,
    CREATE_MESSAGES_TABLE,
    CREATE_USERS_TABLE,
)
from src.utils import (
    profile_to_dict, get_product,
    application_response,
    get_application_or_404,
    get_owned_application_or_404,
    get_owned_conversation_or_404,
    get_owned_profile_or_404, setup_logging,
)
from src.config.database_config import (
    BANK_ROLES, ROLE_BANK_ANALYST,
    ROLE_BANK_MANAGER, ROLE_CLIENT,
    ROLE_SYSTEM
)

logger = logging.getLogger(__name__)
setup_logging()

@asynccontextmanager
async def lifespan(app):
    logger.info("Запуск приложения...")
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
            conn.load_data(CREATE_APPLICATION_STATUS_HISTORY_TABLE)
            conn.load_data(CREATE_USERS_TABLE)
            conn.load_data(CREATE_AUTH_TOKENS_TABLE)
            apply_migrations(conn)
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
        app.state.auth_rep = AuthRepository(dbConn=app.state.dbConn)
    except Exception as e:
        raise RuntimeError(f"[app] Ошибка при инициализации AuthRepository: {e}") from e

    try:
        app.state.llmAPI = LLMApi()
    except Exception as e:
        raise RuntimeError

    logger.info("Приложение успешно запущено!")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def auth_register(
    payload: AuthRegisterRequest,
    auth_rep: AuthRepository = Depends(load_auth_repository),
) -> dict:
    """Регистрация пользователя: создаёт аккаунт и сразу выдаёт токен сессии."""
    try:
        user, token = register_user(auth_rep, payload.username, payload.password, payload.role)
    except UsernameTakenError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except InvalidRoleError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register user: {str(e)}")
    return {"status": "success", "token": token, "user": user_response(user)}


@app.post("/api/auth/login")
def auth_login(
    payload: AuthLoginRequest,
    auth_rep: AuthRepository = Depends(load_auth_repository),
) -> dict:
    """Вход по логину и паролю: выдаёт токен сессии."""
    try:
        user, token = login_user(auth_rep, payload.username, payload.password)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to login: {str(e)}")
    return {"status": "success", "token": token, "user": user_response(user)}


@app.get("/api/auth/me")
def auth_me(user: User = Depends(get_current_user)) -> dict:
    """Текущий пользователь по заголовку Authorization: Bearer <token>."""
    return {"status": "success", "user": user_response(user)}

@app.post("/api/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreateRequest,
    user: User = Depends(get_current_user),
    conv_rep: ConversationRepository = Depends(load_conversation_repository)
) -> dict:
    try:
        new_conversation = Conversation(state=payload.state, user_id=user.id)
        conversation_id = conv_rep.create_conversation(new_conversation)
        return {"status": "success", "id": conversation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")
    
@app.post("/api/conversations/{conversation_id}/messages", status_code=status.HTTP_201_CREATED)
def create_conversation_message(
    conversation_id: int,
    payload: ConversationCreateMessage,
    user: User = Depends(get_current_user),
    conv_rep: ConversationRepository = Depends(load_conversation_repository),
    profile_rep: ProfileRepository = Depends(load_profile_repository),
    llm: LLMApi = Depends(load_LLM),
) -> ContractExtraction:
    """LLM-конвейер обработки сообщения"""
    try:
        get_owned_conversation_or_404(conv_rep, conversation_id, user.id)
        if payload.profile_id is not None:
            get_owned_profile_or_404(profile_rep, payload.profile_id, user.id)

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
    user: User = Depends(get_current_user),
    conv_rep: ConversationRepository = Depends(load_conversation_repository),
) -> dict:
    """Список диалогов пользователя, свежие сверху (для восстановления истории в UI)."""
    try:
        conversations = conv_rep.get_conversations(user_id=user.id)
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
    user: User = Depends(get_current_user),
    conv_rep: ConversationRepository = Depends(load_conversation_repository),
) -> dict:
    """Все сообщения диалога в хронологическом порядке."""
    try:
        get_owned_conversation_or_404(conv_rep, conversation_id, user.id)
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
    user: User = Depends(get_current_user),
    profile_rep: ProfileRepository = Depends(load_profile_repository)
) -> BusinessProfile:
    try:
        new_profile = BusinessProfile(
            user_id=user.id,
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
    user: User = Depends(get_current_user),
    profile_rep: ProfileRepository = Depends(load_profile_repository)
) -> BusinessProfile:
    current = get_owned_profile_or_404(profile_rep, profile_id, user.id)
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
    user: User = Depends(get_current_user),
    profile_rep: ProfileRepository = Depends(load_profile_repository)
) -> BusinessProfile:
    return get_owned_profile_or_404(profile_rep, profile_id, user.id)

@app.post("/api/profile/{profile_id}/payment")
def calc_payment_for_profile(
    profile_id: int,
    user: User = Depends(get_current_user),
    profile_rep: ProfileRepository = Depends(load_profile_repository)
) -> dict:
    """Расчёт аннуитетного платежа по профилю + подбор продукта"""
    profile = get_owned_profile_or_404(profile_rep, profile_id, user.id)

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
    user: User = Depends(get_current_user),
    profile_rep: ProfileRepository = Depends(load_profile_repository),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Создание черновика заявки: валидация профиля/продукта + аннуитетный расчёт"""
    profile = get_owned_profile_or_404(profile_rep, payload.profile_id, user.id)

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
        status=STATUS_DRAFT,
        client_data=payload.client_data.model_dump(mode="json") if payload.client_data is not None else None,
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
    user: User = Depends(get_current_user),
    profile_rep: ProfileRepository = Depends(load_profile_repository),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Повторная обработка заявки: submitted|needs_info -> конвейер скоринга."""
    get_owned_application_or_404(app_rep, profile_rep, application_id, user.id)
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


@app.post("/api/applications/{application_id}/submit")
def submit_application(
    application_id: int,
    user: User = Depends(get_current_user),
    profile_rep: ProfileRepository = Depends(load_profile_repository),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Отправка заявки на обработку: draft -> submitted + автозапуск конвейера."""
    application = get_owned_application_or_404(app_rep, profile_rep, application_id, user.id)
    try:
        transition_application(application, STATUS_SUBMITTED, ROLE_CLIENT, user.id, app_rep)
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


@app.patch("/api/applications/{application_id}")
def update_application(
    application_id: int,
    payload: ApplicationUpdateRequest,
    user: User = Depends(get_current_user),
    profile_rep: ProfileRepository = Depends(load_profile_repository),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Редактирование черновика заявки: сумма/срок с пересчётом аннуитета."""
    application = get_owned_application_or_404(app_rep, profile_rep, application_id, user.id)
    if application.status != STATUS_DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only draft applications can be edited (current: '{application.status}')",
        )

    product = get_product(application.product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id={application.product_id} not found",
        )

    amount = (
        float(payload.requested_amount)
        if payload.requested_amount is not None
        else application.requested_amount
    )
    term = payload.term_months if payload.term_months is not None else application.term_months
    if not product["min_amount"] <= amount <= product["max_amount"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Requested amount must be between {product['min_amount']} and "
                f"{product['max_amount']} for product '{product['name']}'"
            ),
        )
    if not product["min_term"] <= term <= product["max_term"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Term must be between {product['min_term']} and {product['max_term']} "
                f"months for product '{product['name']}'"
            ),
        )

    monthly_payment = calculate_annuity_payment(amount, float(product["rate"]), term)
    total_repayment = round(monthly_payment * term, 4)
    overpayment = round(total_repayment - amount, 4)

    application.requested_amount = amount
    application.term_months = term
    application.monthly_payment = monthly_payment
    application.total_repayment = total_repayment
    application.overpayment = overpayment
    application.updated_at = datetime.now(timezone.utc)
    try:
        if app_rep.update_application_details(application) is None:
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


@app.post("/api/applications/{application_id}/offer-response")
def respond_to_offer(
    application_id: int,
    payload: ApplicationOfferResponseRequest,
    user: User = Depends(get_current_user),
    profile_rep: ProfileRepository = Depends(load_profile_repository),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Отклик клиента на предложение: offer_ready -> accepted | client_declined."""
    application = get_owned_application_or_404(app_rep, profile_rep, application_id, user.id)
    target_status = STATUS_ACCEPTED if payload.accept else STATUS_CLIENT_DECLINED
    comment = f"Причина отказа: {payload.decline_reason}" if (
        not payload.accept and payload.decline_reason
    ) else None
    try:
        application = transition_application(
            application, target_status, ROLE_CLIENT, user.id, app_rep, comment=comment
        )
    except InvalidApplicationStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return {"status": "success", "application": application_response(application)}


@app.post("/api/applications/{application_id}/sign")
def sign_application(
    application_id: int,
    user: User = Depends(get_current_user),
    profile_rep: ProfileRepository = Depends(load_profile_repository),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Подписание договора (ЭП моделируется кнопкой): accepted -> signed -> issued."""
    application = get_owned_application_or_404(app_rep, profile_rep, application_id, user.id)
    try:
        application = transition_application(
            application, STATUS_SIGNED, ROLE_CLIENT, user.id, app_rep,
            comment="Договор подписан (ЭП)",
        )
        application = transition_application(
            application, STATUS_ISSUED, ROLE_SYSTEM, None, app_rep,
            comment="Договор подписан, выдача исполнена",
        )
    except InvalidApplicationStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return {"status": "success", "application": application_response(application)}


@app.get("/api/applications/{application_id}/history")
def get_application_history(
    application_id: int,
    user: User = Depends(get_current_user),
    profile_rep: ProfileRepository = Depends(load_profile_repository),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """История смены статуса заявки, от ранней записи к поздней."""
    get_owned_application_or_404(app_rep, profile_rep, application_id, user.id)
    try:
        history = app_rep.get_status_history(application_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")
    return {"status": "success", "application_id": application_id, "history": history}


@app.post("/api/applications/{application_id}/explain")
def explain_application(
    application_id: int,
    payload: ApplicationExplainRequest | None = None,
    user: User = Depends(get_current_user),
    profile_rep: ProfileRepository = Depends(load_profile_repository),
    app_rep: ApplicationRepository = Depends(load_application_repository),
    llm: LLMApi = Depends(load_LLM),
) -> dict:
    """ИИ-объяснение решения по заявке только по зафиксированным факторам из decision_details"""
    application = get_owned_application_or_404(app_rep, profile_rep, application_id, user.id)
    if not application.decision or not application.decision_details:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Explanation is available only after a decision is made "
                f"(current status: '{application.status}')"
            ),
        )
    audience = payload.audience if payload is not None else "client"
    try:
        result = explain_application_decision(
            llm, application_response(application), audience
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to explain decision: {str(e)}")
    return {"status": "success", "application_id": application_id, **result}


@app.get("/api/applications/{application_id}")
def get_application(
    application_id: int,
    user: User = Depends(get_current_user),
    profile_rep: ProfileRepository = Depends(load_profile_repository),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Заявка пользователя по id со статусом и результатом скоринга."""
    application = get_owned_application_or_404(app_rep, profile_rep, application_id, user.id)
    return {"status": "success", "application": application_response(application)}


@app.get("/api/profile/{profile_id}/applications")
def get_profile_applications(
    profile_id: int,
    user: User = Depends(get_current_user),
    profile_rep: ProfileRepository = Depends(load_profile_repository),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Все заявки профиля пользователя, новые сверху."""
    get_owned_profile_or_404(profile_rep, profile_id, user.id)
    try:
        applications = app_rep.get_applications_by_profile(profile_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list applications: {str(e)}")
    return {
        "status": "success",
        "profile_id": profile_id,
        "applications": [application_response(a) for a in applications],
    }


@app.get("/api/me/applications")
def get_my_applications(
    user: User = Depends(get_current_user),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Все заявки текущего пользователя (по всем его профилям), новые сверху.

    Фронтенд синхронизирует по этому эндпоинту статусы заявок клиента —
    решения банка (ручная экспертиза, предложение) видны без действий клиента.
    """
    try:
        applications = app_rep.get_applications_by_user(user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list applications: {str(e)}")
    return {"status": "success", "applications": [application_response(a) for a in applications]}


@app.get("/api/me/profile", response_model=BusinessProfile)
def get_my_profile(
    user: User = Depends(get_current_user),
    profile_rep: ProfileRepository = Depends(load_profile_repository),
) -> BusinessProfile:
    """Последний профиль текущего пользователя — восстановление сессии клиента.

    404 — если у пользователя ещё нет профилей (клиент создаст его при первом сообщении).
    """
    try:
        profile = profile_rep.get_latest_profile_by_user(user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile for current user not found",
        )
    return profile


@app.get("/api/admin/applications")
def admin_list_applications(
    status_filter: str | None = Query(default=None, alias="status"),
    user: User = Depends(require_role(*BANK_ROLES)),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Очередь заявок для сотрудников банка: все заявки, новые сверху (п. 2.5)."""
    if status_filter is not None and status_filter not in APPLICATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown status {status_filter!r}; must be one of {APPLICATION_STATUSES}",
        )
    try:
        applications = app_rep.get_all_applications(status_filter)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list applications: {str(e)}")
    return {"status": "success", "applications": [application_response(a) for a in applications]}


@app.post("/api/admin/applications/{application_id}/request-info")
def admin_request_info(
    application_id: int,
    payload: AdminRequestInfoRequest,
    user: User = Depends(require_role(ROLE_BANK_MANAGER)),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Менеджер запрашивает уточнения: data_check|scoring|manual_review -> needs_info."""
    application = get_application_or_404(app_rep, application_id)
    application.decision_details = {
        **(application.decision_details or {}),
        "needs_info_reason": payload.message,
    }
    try:
        application = transition_application(
            application, STATUS_NEEDS_INFO, ROLE_BANK_MANAGER, user.id, app_rep,
            comment=payload.message,
        )
    except InvalidApplicationStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return {"status": "success", "application": application_response(application)}


@app.post("/api/admin/applications/{application_id}/assign-analyst")
def admin_assign_analyst(
    application_id: int,
    user: User = Depends(require_role(ROLE_BANK_MANAGER)),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Менеджер передаёт заявку на ручную экспертизу: data_check|scoring -> manual_review."""
    application = get_application_or_404(app_rep, application_id)
    try:
        application = transition_application(
            application, STATUS_MANUAL_REVIEW, ROLE_BANK_MANAGER, user.id, app_rep,
            comment="Заявка передана кредитному аналитику",
        )
    except InvalidApplicationStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return {"status": "success", "application": application_response(application)}


@app.post("/api/admin/applications/{application_id}/decision")
def admin_decision(
    application_id: int,
    payload: AdminDecisionRequest,
    user: User = Depends(require_role(ROLE_BANK_ANALYST)),
    app_rep: ApplicationRepository = Depends(load_application_repository),
) -> dict:
    """Решение аналитика по заявке в ручной экспертизе: approved*|rejected с причиной."""
    application = get_application_or_404(app_rep, application_id)
    application.decision = payload.decision
    application.decision_details = {
        **(application.decision_details or {}),
        "analyst_decision": {
            "decision": payload.decision,
            "reason": payload.reason,
            "analyst": user.username,
        },
    }
    try:
        application = transition_application(
            application, payload.decision, ROLE_BANK_ANALYST, user.id, app_rep,
            comment=payload.reason,
        )
        if payload.decision in (STATUS_APPROVED, STATUS_APPROVED_WITH_CHANGES):
            application = transition_application(
                application, STATUS_OFFER_READY, ROLE_SYSTEM, None, app_rep,
                comment="Предложение сформировано",
            )
    except InvalidApplicationStatusError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return {"status": "success", "application": application_response(application)}


@app.get("/api/registry/{inn}")
def get_registry(inn: str) -> dict:
    """Тестовый реестр: данные компании и руководителя по ИНН (мок справочника)"""
    entry = get_registry_entry(inn)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registry entry for inn={inn} not found",
        )
    return {"status": "success", **entry}


@app.get("/api/products")
def get_products() -> list[dict]:
    """Каталог кредитных продуктов"""
    return PRODUCTS




if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5555")),
        log_config=None,
    )