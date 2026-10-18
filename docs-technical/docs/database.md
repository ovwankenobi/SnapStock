# Database Schema

PostgreSQL, accessed through SQLAlchemy models in `backend/app/models/`. Every table uses a UUID
primary key and UTC-aware timestamps via the shared mixins in `models/mixins.py`
(`UUIDPkMixin`, `CreatedAtMixin`, `UpdatedAtMixin`).

```mermaid
erDiagram
    USERS ||--o| SELLER_PROFILES : "has (if role=seller)"
    SELLER_PROFILES ||--o{ SELLER_PAYOUT_ACCOUNTS : "receives payments via"
    USERS ||--o{ PRODUCTS : "sells (seller_id)"
    USERS ||--o{ SALES : "sells as (seller_id)"
    USERS |o--o{ SALES : "buys as (buyer_id, nullable)"
    USERS ||--o{ CONVERSATIONS : "participates as seller"
    USERS ||--o{ CONVERSATIONS : "participates as buyer"
    USERS ||--o{ MESSAGES : "sends (sender_id)"

    PRODUCTS ||--o{ SALE_ITEMS : "sold as (product_id, nullable)"
    PRODUCTS ||--o{ STOCK_MOVEMENTS : "tracked by"
    PRODUCTS ||--o{ PRODUCT_COST_HISTORY : "cost logged in"
    PRODUCTS |o--o{ CONVERSATIONS : "discussed in (product_id, nullable)"

    SALES ||--o{ SALE_ITEMS : "contains"
    SALES |o--o{ STOCK_MOVEMENTS : "caused (sale_id, nullable)"

    SALES |o--o{ MESSAGES : "order card (sale_id, nullable)"

    CONVERSATIONS ||--o{ MESSAGES : "contains"

    USERS {
        uuid id PK
        string email UK
        string hashed_password
        string full_name
        enum role "seller | buyer"
        string phone
        string preferred_language
        bool is_active
    }
    SELLER_PROFILES {
        uuid id PK
        uuid user_id FK "unique -> users.id"
        string business_name
        enum business_type "wholesale | retail | both"
        text address
        text description
    }
    SELLER_PAYOUT_ACCOUNTS {
        uuid id PK
        uuid seller_profile_id FK "-> seller_profiles.id, cascade delete"
        enum method "gcash | maya | bank_transfer | other (never cash)"
        string account_name
        string account_number
        string bank_name "NULLABLE: bank, or provider for other"
        string qr_url "NULLABLE"
        bool is_default
    }
    PRODUCTS {
        uuid id PK
        uuid seller_id FK "-> users.id"
        string name
        int price_cents
        int cost_cents "NULLABLE: unit cost, same unit as price"
        enum unit_type "piece | bundle | measure"
        string unit_label "measure only: kg, yd, m, ..."
        int pieces_per_unit
        int stock_pieces "pieces; thousandths of unit for measure"
        int low_stock_threshold
        string category
        bool is_active "soft delete"
    }
    SALES {
        uuid id PK
        uuid seller_id FK "-> users.id"
        uuid buyer_id FK "-> users.id, NULLABLE"
        enum sale_type "itemized | walk_in"
        int subtotal_cents "sum of line totals at charged prices"
        int discount_cents "sale-level, default 0"
        int total_cents "subtotal - discount"
        enum status "completed | voided | refunded | pending_payment | cancelled"
        timestamptz status_changed_at "NULLABLE"
        text status_reason "NULLABLE, seller-only"
        enum payment_method
        string receipt_code UK
        text note
        string payment_proof_url "NULLABLE: buyer's screenshot, never public"
        timestamptz proof_submitted_at "NULLABLE"
    }
    SALE_ITEMS {
        uuid id PK
        uuid sale_id FK "-> sales.id, cascade delete"
        uuid product_id FK "-> products.id, NULLABLE"
        string product_name_snapshot
        int list_price_cents_snapshot "product price at sale time"
        int unit_price_cents_snapshot "price actually charged"
        int unit_cost_cents_snapshot "NULLABLE: cost at sale time"
        int cost_total_cents "NULLABLE: line COGS"
        int quantity
        enum unit_type_snapshot
        string unit_label_snapshot
        int pieces_deducted
        int line_total_cents
    }
    STOCK_MOVEMENTS {
        uuid id PK
        uuid product_id FK "-> products.id"
        int change_pieces "signed: + restock, - sale"
        enum reason "sale | quick_sell | restock | correction | initial | void | refund | cancel"
        uuid sale_id FK "-> sales.id, NULLABLE"
        text note
    }
    PRODUCT_COST_HISTORY {
        uuid id PK
        uuid product_id FK "-> products.id"
        int cost_cents
        enum source "manual | restock"
    }
    CONVERSATIONS {
        uuid id PK
        uuid seller_id FK "-> users.id"
        uuid buyer_id FK "-> users.id"
        uuid product_id FK "-> products.id, NULLABLE"
        timestamptz last_message_at
    }
    MESSAGES {
        uuid id PK
        uuid conversation_id FK "-> conversations.id"
        uuid sender_id FK "-> users.id"
        text body
        uuid sale_id FK "-> sales.id, NULLABLE: order card"
        timestamptz read_at "NULL until read"
    }
```

## Why `buyer_id` is nullable

`sales.buyer_id` is nullable because `sale_type = walk_in` (an anonymous cash sale rung up at the
stall, with no buyer account involved) and `sale_type = itemized` (a buyer-linked digital order)
share one table. A walk-in sale simply never sets `buyer_id`; `SaleCreate.check_consistency`
enforces the pairing at the API boundary (`itemized` requires a `buyer_id`, `walk_in` forbids
one). Both sale types deduct stock and count toward analytics identically — no code branches on
`sale_type` for that shared behavior, only for what's required on the way in and what's shown on
receipts (buyer name vs. "Walk-in").

## Other notable design choices

- **`sale_items.product_id` is nullable and the row snapshots `product_name_snapshot`,
  `unit_price_cents_snapshot`, `unit_type_snapshot`, `unit_label_snapshot` at write time.** Products are soft-deleted
  (`is_active = false`) only — never hard-deleted, because `sale_items` (and therefore every past
  receipt) references them by ID. The snapshot columns mean a receipt's wording and price never
  change even if the product is later renamed or re-priced.
- **`stock_movements` is append-only** and is the audit trail for every change to
  `products.stock_pieces`. `services.inventory.apply_stock_change` is the only code path allowed
  to write `stock_pieces`, and it always writes a matching `stock_movements` row (with `sale_id`
  set when the change came from a sale, `null` for a manual restock).
- **`conversations` has a uniqueness constraint on `(seller_id, buyer_id, product_id)`** so
  re-opening a chat about the same product with the same counterpart reuses the existing thread.
- **`sales.status` covers buyer orders too.** A buyer's online order is a normal `itemized` sale
  created as `pending_payment` (stock already reserved), which becomes `completed` when the seller
  confirms payment or `cancelled` (stock returned with a `cancel` movement) when either side
  backs out. Analytics count only `completed` (plus `refunded` for gross sales and refunds).
- **`messages.sale_id`** marks an order card, the message posted from the buyer when their order
  is ready for review. The API attaches the order's live status to it.
- **`seller_payout_accounts.method` reuses the `payment_method` enum**, so a buyer's chosen method
  maps straight to the seller's matching accounts. The schema layer keeps `cash` out.
- **All money is integer cents** (`price_cents`, `total_cents`, etc.) — there are no floating-point
  currency columns anywhere in the schema.
