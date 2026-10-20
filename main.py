import logging
import uvicorn
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, HTTPException, status
from src.core.llm.extract_pipeline import extract_content
from src.config.products import PRODUCTS
from src.core.llm.LLMApi import LLMApi
from src.core.profile import ProfileRepository
from src.core.recommendations import recommend_products
from src.DI import load_LLM, load_conversation_repository, load_profile_repository
from src.core.conversations import ConversationRepository
from src.database.database import DatabaseConnector
from src.schemas.llm_schema import ContractExtraction
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
    CREATE_BUSINESS_PROFILES_TABLE,
    CREATE_CONVERSATIONS_TABLE,
    CREATE_MESSAGES_TABLE,
)
from src.utils import profile_to_dict

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
    current = profile_rep.get_profile(profile_id)
    if current is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with id={profile_id} not found"
        )
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
    try:
        profile = profile_rep.get_profile(profile_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get profile: {str(e)}"
        )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with id={profile_id} not found"
        )
    return profile

@app.post("/api/profile/{profile_id}/payment")
def calc_payment_for_profile(
    profile_id: int,
    profile_rep: ProfileRepository = Depends(load_profile_repository)
) -> dict:
    try:
        profile = profile_rep.get_profile(profile_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get profile: {str(e)}"
        )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with id={profile_id} not found"
        )

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
    
@app.get("/api/products")
def get_products() -> list[dict]:
    """Каталог кредитных продуктов"""
    return PRODUCTS




if __name__ == "__main__":
    uvicorn.run(host = "127.0.0.1", app = app, port=5555)