from dataclasses import dataclass, field
from datetime import datetime, timezone
from pydantic import BaseModel


@dataclass
class Conversation:
    state: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: int | None = None


@dataclass
class Message:
    conversation_id: int
    role: str
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: int | None = None


class ConversationCreateRequest(BaseModel):
    state: str = "new"


class ConversationCreateMessage(BaseModel):
    role: str = "user"
    content: str
    profile_id: int | None = None