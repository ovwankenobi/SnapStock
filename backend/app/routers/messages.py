import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.conversation import Conversation
from app.models.product import Product
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationListResponse,
    ConversationParticipant,
    ConversationProduct,
    ConversationRead,
    MessageCreate,
    MessageListResponse,
    MessageOrder,
    MessageRead,
)
from app.services import messages as messages_service
from app.services import uploads as uploads_service

router = APIRouter(prefix="/conversations", tags=["messages"])


def _other_user_id(conversation: Conversation, user: User) -> uuid.UUID:
    return conversation.buyer_id if conversation.seller_id == user.id else conversation.seller_id


def _to_conversation_read(
    conversation: Conversation,
    user: User,
    other_user: User,
    product: Product | None,
    unread_count: int,
    last_message_body: str | None,
) -> ConversationRead:
    return ConversationRead(
        id=conversation.id,
        other_user=ConversationParticipant.model_validate(other_user),
        product=ConversationProduct.model_validate(product) if product else None,
        last_message_at=conversation.last_message_at,
        last_message_preview=last_message_body,
        unread_count=unread_count,
        created_at=conversation.created_at,
    )


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversations = messages_service.list_conversations(db, user)
    conv_ids = [c.id for c in conversations]

    other_user_ids = {_other_user_id(c, user) for c in conversations}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(other_user_ids)).all()}

    product_ids = {c.product_id for c in conversations if c.product_id is not None}
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}

    unread = messages_service.unread_counts(db, conv_ids, user)
    last_messages = messages_service.last_messages(db, conv_ids)

    items = [
        _to_conversation_read(
            c,
            user,
            users[_other_user_id(c, user)],
            products.get(c.product_id) if c.product_id else None,
            unread.get(c.id, 0),
            last_messages[c.id].body if c.id in last_messages else None,
        )
        for c in conversations
    ]
    return ConversationListResponse(items=items)


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        conversation = messages_service.get_or_create_conversation(
            db, user, payload.other_user_id, payload.product_id
        )
    except messages_service.UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except messages_service.ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    other_user = db.get(User, _other_user_id(conversation, user))
    product = db.get(Product, conversation.product_id) if conversation.product_id else None
    unread = messages_service.unread_counts(db, [conversation.id], user)
    last = messages_service.last_messages(db, [conversation.id])

    return _to_conversation_read(
        conversation,
        user,
        other_user,
        product,
        unread.get(conversation.id, 0),
        last[conversation.id].body if conversation.id in last else None,
    )


@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
def list_messages(
    conversation_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        conversation = messages_service.get_participant_conversation(db, conversation_id, user)
    except messages_service.ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found") from exc

    items, total = messages_service.list_messages(db, conversation, page, page_size)
    orders = messages_service.orders_for_messages(db, items)
    buyer = db.get(User, conversation.buyer_id) if orders else None

    def to_read(message):
        read = MessageRead.model_validate(message)
        sale = orders.get(message.sale_id)
        if sale is not None:
            read.order = MessageOrder(
                id=sale.id,
                buyer_name=buyer.full_name,
                items_summary=messages_service.order_items_summary(sale),
                total_cents=sale.total_cents,
                payment_method=sale.payment_method,
                status=sale.status,
                payment_proof_url=uploads_service.private_url(sale.payment_proof_url),
            )
        return read

    return MessageListResponse(items=[to_read(m) for m in items], total=total, page=page, page_size=page_size)


@router.post(
    "/{conversation_id}/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED
)
def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        conversation = messages_service.get_participant_conversation(db, conversation_id, user)
    except messages_service.ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found") from exc

    message = messages_service.send_message(db, conversation, user, payload.body)
    return MessageRead.model_validate(message)


@router.post("/{conversation_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        conversation = messages_service.get_participant_conversation(db, conversation_id, user)
    except messages_service.ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found") from exc

    messages_service.mark_read(db, conversation, user)
