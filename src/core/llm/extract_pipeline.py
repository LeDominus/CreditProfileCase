
from dataclasses import replace
from datetime import datetime, timezone
from fastapi import HTTPException, status
from src.schemas.llm_schema import ContractExtraction
from src.core.llm.utils import extract_profile_fields
from src.core.recommendations import recommend_products
from src.core.llm.LLMApi import LLMApi
from src.core.llm.tools import run_with_tools
from src.core.profile import ProfileRepository
from src.schemas.conversation_schema import ConversationCreateMessage, Message
from src.schemas.profile_schema import BusinessProfile
from src.core.conversations import ConversationRepository
from src.utils import FALLBACK_REPLY, profile_to_dict


def extract_content(
    conv_rep: ConversationRepository,
    profile_rep: ProfileRepository,
    llm: LLMApi,
    payload: ConversationCreateMessage,
    conversation_id: int,
    message_id: int,
    ) -> ContractExtraction:
    
    
    profile: BusinessProfile | None = None
    profile_updates: dict = {}
    if payload.profile_id is not None:
        profile = profile_rep.get_profile(payload.profile_id)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile with id={payload.profile_id} not found"
            )
        profile_updates = extract_profile_fields(
            payload.content, llm, profile_to_dict(profile)
        )
        if profile_updates:
            updated = replace(profile, **profile_updates)
            updated.updated_at = datetime.now(timezone.utc)
            profile_rep.update_profile(updated)
            profile = profile_rep.get_profile(profile.id)

    profile_dict = profile_to_dict(profile) if profile is not None else None
    history = conv_rep.get_conversation_messages(conversation_id)
    context = llm.extract_context(messages=history, profile=profile_dict)
    try:
        reply = run_with_tools(llm, context)
    except Exception:
        reply = ""
    if not reply or not reply.strip():
        reply = FALLBACK_REPLY
    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=reply
    )
    assistant_message_id = conv_rep.send_conversation_message(assistant_message)

    recommendations: list[dict] = []
    if (
        profile_dict is not None
        and profile_dict.get("requested_amount") is not None
        and profile_dict.get("preferred_term_months") is not None
    ):
        recommendations = recommend_products(profile_dict)
    
    return ContractExtraction(
        status="success",
        id=message_id,
        assistant_message_id=assistant_message_id,
        conversation_id=conversation_id,
        reply=reply,
        profile_updates=profile_updates,
        profile={**profile_dict, "id": profile.id} if profile is not None else None,
        recommendations=recommendations
    )