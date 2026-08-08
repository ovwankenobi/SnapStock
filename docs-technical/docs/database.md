# Database Schema

PostgreSQL, accessed through SQLAlchemy models in `backend/app/models/`. Every table uses a UUID
primary key and UTC-aware timestamps via the shared mixins in `models/mixins.py`
(`UUIDPkMixin`, `CreatedAtMixin`, `UpdatedAtMixin`).

```mermaid
erDiagram
    USERS ||--o| SELLER_PROFILES : "has (if role=seller)"
    USERS ||--o{ PRODUCTS : "sells (seller_id)"
    USERS ||--o{ SALES : "sells as (seller_id)"
    USERS |o--o{ SALES : "buys as (buyer_id, nullable)"
    USERS ||--o{ CONVERSATIONS : "participates as seller"
    USERS ||--o{ CONVERSATIONS : "participates as buyer"
    USERS ||--o{ MESSAGES : "sends (sender_id)"

    PRODUCTS ||--o{ SALE_ITEMS : "sold as (product_id, nullable)"
    PRODUCTS ||--o{ STOCK_MOVEMENTS : "tracked by"
    PRODUCTS |o--o{ CONVERSATIONS : "discussed in (product_id, nullable)"

    SALES ||--o{ SALE_ITEMS : "contains"
    SALES |o--o{ STOCK_MOVEMENTS : "caused (sale_id, nullable)"

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
    PRODUCTS {
        uuid id PK
        uuid seller_id FK "-> users.id"
        string name
        int price_cents
        enum unit_type "piece | bundle | grams"
        int pieces_per_unit
        int stock_pieces "always in pieces"
        int low_stock_threshold
        string category
        bool is_active "soft delete"
    }
    SALES {
        uuid id PK
        uuid seller_id FK "-> users.id"
        uuid buyer_id FK "-> users.id, NULLABLE"
        enum sale_type "itemized | walk_in"
        int total_cents
        enum payment_method
        string receipt_code UK
        text note
    }
    SALE_ITEMS {
        uuid id PK
        uuid sale_id FK "-> sales.id, cascade delete"
        uuid product_id FK "-> products.id, NULLABLE"
        string product_name_snapshot
        int unit_price_cents_snapshot
        int quantity
        enum unit_type_snapshot
        int pieces_deducted
        int line_total_cents
    }
    STOCK_MOVEMENTS {
        uuid id PK
        uuid product_id FK "-> products.id"
        int change_pieces "signed: + restock, - sale"
        enum reason "sale | quick_sell | restock | correction | initial"
        uuid sale_id FK "-> sales.id, NULLABLE"
        text note
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
  `unit_price_cents_snapshot`, `unit_type_snapshot` at write time.** Products are soft-deleted
  (`is_active = false`) only — never hard-deleted, because `sale_items` (and therefore every past
  receipt) references them by ID. The snapshot columns mean a receipt's wording and price never
  change even if the product is later renamed or re-priced.
- **`stock_movements` is append-only** and is the audit trail for every change to
  `products.stock_pieces`. `services.inventory.apply_stock_change` is the only code path allowed
  to write `stock_pieces`, and it always writes a matching `stock_movements` row (with `sale_id`
  set when the change came from a sale, `null` for a manual restock).
- **`conversations` has a uniqueness constraint on `(seller_id, buyer_id, product_id)`** so
  re-opening a chat about the same product with the same counterpart reuses the existing thread.
- **All money is integer cents** (`price_cents`, `total_cents`, etc.) — there are no floating-point
  currency columns anywhere in the schema.
