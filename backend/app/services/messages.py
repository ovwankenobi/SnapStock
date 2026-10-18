import uuid
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models.conversation import Conversation, Message
from app.models.product import Product
from app.models.sale import PaymentMethod, Sale
from app.models.user import User, UserRole


class UserNotFoundError(Exception):
    pass


class ProductNotFoundError(Exception):
    pass


class ConversationNotFoundError(Exception):
    pass


def _resolve_participants(
    db: Session, current_user: User, other_user_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID]:
    other_user = db.get(User, other_user_id)
    if other_user is None or not other_user.is_active:
        raise UserNotFoundError("User not found")

    if current_user.role == UserRole.SELLER:
        if other_user.role != UserRole.BUYER:
            raise UserNotFoundError("Buyer not found")
        return current_user.id, other_user.id
    else:
        if other_user.role != UserRole.SELLER:
            raise UserNotFoundError("Seller not found")
        return other_user.id, current_user.id


def get_or_create_conversation(
    db: Session,
    current_user: User,
    other_user_id: uuid.UUID,
    product_id: uuid.UUID | None,
) -> Conversation:
    seller_id, buyer_id = _resolve_participants(db, current_user, other_user_id)

    if product_id is not None:
        product = db.get(Product, product_id)
        if product is None or not product.is_active or product.seller_id != seller_id:
            raise ProductNotFoundError("Product not found")

    query = db.query(Conversation).filter(
        Conversation.seller_id == seller_id, Conversation.buyer_id == buyer_id
    )
    query = (
        query.filter(Conversation.product_id == product_id)
        if product_id is not None
        else query.filter(Conversation.product_id.is_(None))
    )
    existing = query.first()
    if existing is not None:
        return existing

    conversation = Conversation(seller_id=seller_id, buyer_id=buyer_id, product_id=product_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def list_conversations(db: Session, user: User) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter((Conversation.seller_id == user.id) | (Conversation.buyer_id == user.id))
        .order_by(Conversation.last_message_at.desc())
        .all()
    )


def get_participant_conversation(db: Session, conversation_id: uuid.UUID, user: User) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or user.id not in (conversation.seller_id, conversation.buyer_id):
        raise ConversationNotFoundError("Conversation not found")
    return conversation


def list_messages(
    db: Session, conversation: Conversation, page: int = 1, page_size: int = 30
) -> tuple[list[Message], int]:
    query = db.query(Message).filter(Message.conversation_id == conversation.id)
    total = query.count()
    items = (
        query.order_by(Message.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def send_message(db: Session, conversation: Conversation, sender: User, body: str) -> Message:
    message = Message(conversation_id=conversation.id, sender_id=sender.id, body=body)
    db.add(message)
    conversation.last_message_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)
    return message


def mark_read(db: Session, conversation: Conversation, user: User) -> None:
    db.query(Message).filter(
        Message.conversation_id == conversation.id,
        Message.sender_id != user.id,
        Message.read_at.is_(None),
    ).update({"read_at": datetime.now(timezone.utc)}, synchronize_session=False)
    db.commit()


def unread_counts(db: Session, conversation_ids: list[uuid.UUID], user: User) -> dict[uuid.UUID, int]:
    if not conversation_ids:
        return {}
    rows = (
        db.query(Message.conversation_id, func.count(Message.id))
        .filter(
            Message.conversation_id.in_(conversation_ids),
            Message.sender_id != user.id,
            Message.read_at.is_(None),
        )
        .group_by(Message.conversation_id)
        .all()
    )
    return dict(rows)


def last_messages(db: Session, conversation_ids: list[uuid.UUID]) -> dict[uuid.UUID, Message]:
    if not conversation_ids:
        return {}
    rows = (
        db.query(Message)
        .filter(Message.conversation_id.in_(conversation_ids))
        .distinct(Message.conversation_id)
        .order_by(Message.conversation_id, Message.created_at.desc())
        .all()
    )
    return {message.conversation_id: message for message in rows}


def order_items_summary(sale: Sale) -> str:
    return ", ".join(item.product_name_snapshot for item in sale.items)


def post_order_card(db: Session, sale: Sale, buyer: User) -> Message:
    """Post "<buyer> bought this — approve?" from the buyer into their chat with the seller.

    Sent when an online order becomes reviewable: a cash order once placed, a digital one each time
    the buyer uploads proof of payment. The card links to the order, so it always shows the live status.
    """
    product_id = sale.items[0].product_id if sale.items else None
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.seller_id == sale.seller_id,
            Conversation.buyer_id == buyer.id,
            Conversation.product_id == product_id
            if product_id is not None
            else Conversation.product_id.is_(None),
        )
        .first()
    )
    if conversation is None:
        conversation = Conversation(seller_id=sale.seller_id, buyer_id=buyer.id, product_id=product_id)
        db.add(conversation)
        db.flush()

    total = f"₱{sale.total_cents / 100:,.2f}"
    bought = f"{buyer.full_name} bought {order_items_summary(sale)} ({total})"
    if sale.payment_method == PaymentMethod.CASH:
        body = f"{bought} and will pay in cash. Approve or not?"
    else:
        body = f"{bought}. Here is the proof of payment — approve or not?"

    message = Message(conversation_id=conversation.id, sender_id=buyer.id, body=body, sale_id=sale.id)
    db.add(message)
    conversation.last_message_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)
    return message


def orders_for_messages(db: Session, messages: list[Message]) -> dict[uuid.UUID, Sale]:
    sale_ids = {m.sale_id for m in messages if m.sale_id is not None}
    if not sale_ids:
        return {}
    sales = db.query(Sale).options(selectinload(Sale.items)).filter(Sale.id.in_(sale_ids)).all()
    return {sale.id: sale for sale in sales}
