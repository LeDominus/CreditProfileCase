
from dataclasses import replace
from datetime import datetime, timezone
from src.schemas.llm_schema import ContractExtraction
from src.config.llm_config import REQUIRED_PROFILE_FIELDS
from src.core.llm.utils import extract_profile_fields, validate_profile_fields
from src.core.recommendations import recommend_products
from src.core.llm.LLMApi import LLMApi
from src.core.llm.tools import run_dialogue
from src.core.profile import ProfileRepository
from src.schemas.conversation_schema import ConversationCreateMessage, Message
from src.schemas.profile_schema import BusinessProfile
from src.core.conversations import ConversationRepository
from src.config.prompt import FALLBACK_REPLY
from src.utils import get_profile_or_404, profile_to_dict


def extract_content(
    conv_rep: ConversationRepository,
    profile_rep: ProfileRepository,
    llm: LLMApi,
    payload: ConversationCreateMessage,
    conversation_id: int,
    message_id: int,
    ) -> ContractExtraction:
    
    
    profile: BusinessProfile | None = None
    if payload.profile_id is not None:
        profile = get_profile_or_404(profile_rep, payload.profile_id)
    profile_dict = profile_to_dict(profile) if profile is not None else None

    history = conv_rep.get_conversation_messages(conversation_id)
    context = llm.extract_context(
        messages=history, profile=profile_dict, require_complete_profile=True
    )
    try:
        result = run_dialogue(llm, context)
    except Exception:
        result = {"reply": "", "profile_updates": {}, "parsed": False}

    profile_updates = validate_profile_fields(result.get("profile_updates"))
    if profile is not None and not result.get("parsed"):
        # модель нарушила JSON-формат ответа — запасное извлечение полей
        # отдельным запросом на модели для экстракции
        profile_updates = extract_profile_fields(payload.content, llm, profile_dict)
    if profile is not None and profile_updates:
        updated = replace(profile, **profile_updates)
        updated.updated_at = datetime.now(timezone.utc)
        profile_rep.update_profile(updated)
        profile = profile_rep.get_profile(profile.id)
        profile_dict = profile_to_dict(profile)

    reply = str(result.get("reply") or "").strip()
    if not reply:
        reply = FALLBACK_REPLY
    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=reply
    )
    assistant_message_id = conv_rep.send_conversation_message(assistant_message)

    recommendation_required_fields = (
        "requested_amount",
        "preferred_term_months",
        *REQUIRED_PROFILE_FIELDS,
    )
    recommendations: list[dict] = []
    if profile_dict is not None and all(
        profile_dict.get(field) is not None for field in recommendation_required_fields
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