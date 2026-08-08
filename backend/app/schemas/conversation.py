import uuid
from datetime import datetime

from pydantic import Field

from app.models.user import UserRole
from app.schemas.base import CamelModel


class ConversationParticipant(CamelModel):
    id: uuid.UUID
    full_name: str
    role: UserRole


class ConversationProduct(CamelModel):
    id: uuid.UUID
    name: str
    photo_url: str | None
    price_cents: int


class ConversationCreate(CamelModel):
    other_user_id: uuid.UUID
    product_id: uuid.UUID | None = None


class ConversationRead(CamelModel):
    id: uuid.UUID
    other_user: ConversationParticipant
    product: ConversationProduct | None = None
    last_message_at: datetime
    last_message_preview: str | None = None
    unread_count: int
    created_at: datetime


class ConversationListResponse(CamelModel):
    items: list[ConversationRead]


class MessageCreate(CamelModel):
    body: str = Field(min_length=1)


class MessageRead(CamelModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    body: str
    created_at: datetime
    read_at: datetime | None


class MessageListResponse(CamelModel):
    items: list[MessageRead]
    total: int
    page: int
    page_size: int
