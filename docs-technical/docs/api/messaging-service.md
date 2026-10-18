# Messaging Service

One-to-one conversations between a seller and a buyer, optionally pinned to a product. Router:
`app/routers/messages.py` (prefix `/conversations`), business logic in
`app/services/messages.py`. All endpoints require `Authorization: Bearer <token>`
(`get_current_user` — either role, not seller/buyer-restricted) and are scoped to conversations
the caller participates in.

A `(seller_id, buyer_id, product_id)` triple is unique (`uq_conversations_seller_buyer_product`)
— starting a new conversation with the same counterpart about the same product returns the
existing one instead of creating a duplicate.

## `GET /conversations`

List the caller's conversations (as either the seller or buyer side), newest activity first
(`last_message_at` descending).

**Response (`ConversationListResponse`):** `items[]`, each with `otherUser` (`id`, `fullName`,
`role`), `product` (pinned product summary, or `null`), `lastMessageAt`, `lastMessagePreview`,
`unreadCount`, `createdAt`.

## `POST /conversations`

Start (or resume) a conversation with another user, optionally about a specific product.

**Request (`ConversationCreate`):** `{ otherUserId: UUID, productId?: UUID }`

Server-side, the seller/buyer sides are inferred from the caller's own role and the other user's
role (a seller can only start a conversation with a buyer, and vice versa —
`_resolve_participants`). If `productId` is given, it must be an active product belonging to the
seller side of the conversation.

**Response:** `ConversationRead` (201). **Errors:** `404` if the other user or product doesn't
resolve to a valid counterpart.

## `GET /conversations/{conversationId}/messages`

Paginated message history, newest first (`page`, `pageSize`, default 30/page, max 100).

**Response:** `MessageListResponse` — `{ items: MessageRead[], total, page, pageSize }`. Each
`MessageRead` has `id`, `conversationId`, `senderId`, `body`, `createdAt`, `readAt` (`null` until
read), `saleId` and `order`. Both are `null` on ordinary messages.

**Errors:** `404` if the conversation doesn't exist or the caller isn't a participant.

## `POST /conversations/{conversationId}/messages`

Send a message. Also bumps `conversation.last_message_at` to now.

**Request (`MessageCreate`):** `{ body: string (min length 1) }`
**Response:** `MessageRead` (201).

## `POST /conversations/{conversationId}/read`

Marks every message in the conversation **not** sent by the caller as read (`read_at = now()`).
Used to zero out the unread badge when a conversation is opened. Returns `204`, no body.

---

## Order cards

When a buyer's online order becomes ready for the seller to review, the backend posts a message
**from the buyer** into their conversation with the seller (`services/messages.post_order_card`):

- a **cash** order, as soon as it is placed;
- a **digital** order (GCash, Maya, bank, other), each time the buyer uploads a payment
  screenshot.

The message goes into the conversation for that seller, buyer and the order's first product, and
is created if it doesn't exist yet. Its `body` is plain text (e.g. *"Ana bought Pork belly
(₱350.00) and will pay in cash. Approve or not?"*), so it reads correctly as a list preview. Its
`messages.sale_id` points at the order.

`GET .../messages` attaches the order's **live** state as `order` (`MessageOrder`: `id`,
`buyerName`, `itemsSummary`, `totalCents`, `paymentMethod`, `status`, `paymentProofUrl`). The card
always shows the current status, even after the order was approved or cancelled.
`features/messages/OrderCardBubble.jsx` renders it. While the order is pending, the seller gets
**Review & approve**, which opens `/sales?path=account&order=<id>` (see
[Sales Service](sales-service.md)). Otherwise the button is **View order**, which takes the buyer
to `/buyer/orders/<id>`.

---

Delivery is poll-based on the frontend (`ConversationListPage`/`ChatPage` refetch every 6–8s via
TanStack Query's `refetchInterval`) — there is no WebSocket/push channel. See
[Deferred Features](../deferred-features.md).
