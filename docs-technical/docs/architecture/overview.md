# Architecture Overview

Public Market POS is a single FastAPI application (not separate microservices) whose routers
delegate to distinct service modules — inventory, sales, messaging, catalog, analytics — all
sharing one PostgreSQL database. The Seller and Buyer apps are two React route trees in the same
frontend codebase, gated by role (`ProtectedRoute role="seller"|"buyer"` in `App.jsx`).

```mermaid
flowchart TB
    SellerApp["Seller App<br/>(React — /dashboard, /inventory, /sales, /analytics)"]
    BuyerApp["Buyer App<br/>(React — /buyer, /buyer/products, /buyer/receipts)"]

    subgraph Backend["FastAPI backend — /api/v1"]
        Inventory["Inventory Service<br/>(app/routers/inventory.py + app/services/inventory.py)"]
        Sales["Sales Service<br/>(app/routers/sales.py + catalog.py + app/services/sales.py)"]
        Messaging["Messaging Service<br/>(app/routers/messages.py + app/services/messages.py)"]
    end

    DB[("PostgreSQL<br/>products, sales, sale_items,<br/>stock_movements, users, conversations")]

    SellerApp -->|"CRUD products, quick-sell, restock, photo upload"| Inventory
    SellerApp -->|"create/list sales, buyer search, receipts"| Sales
    SellerApp -->|"list/send messages"| Messaging

    BuyerApp -->|"browse catalog, image search"| Inventory
    BuyerApp -->|"place order, my receipts"| Sales
    BuyerApp -->|"message seller"| Messaging

    Sales -.->|"apply_stock_change() deducts stock<br/>in the same DB transaction"| Inventory

    Inventory -->|"read/write"| DB
    Sales -->|"read/write"| DB
    Messaging -->|"read/write"| DB
```

A few things worth calling out:

- **Catalog is buyer-facing inventory + sales, not a fourth service.** `app/routers/catalog.py`
  reads `Product` rows (the same table Inventory owns) for browsing, and calls
  `services.sales.create_sale` directly for the `POST /catalog/products/{id}/order` endpoint — it
  is a thin façade over the other two services, not an independent domain.
- **Sales never mutates stock directly.** `services/sales.create_sale` and
  `services/inventory.quick_sell` both call `services.inventory.apply_stock_change`, which is the
  only function allowed to write `Product.stock_pieces`. That function row-locks the product
  (`SELECT ... FOR UPDATE`), rejects changes that would go negative, and writes an append-only
  `stock_movements` row — all in the same transaction as the sale.
- **Auth and Analytics aren't pictured above** for clarity (one process per diagram) — `auth`
  issues JWTs consumed by every other router via `get_current_user`/`require_seller`/
  `require_buyer` (`app/core/deps.py`), and `analytics` is a read-only aggregation layer over the
  same `sales`/`products` tables the Sales and Inventory services own.

See [Data Flow](data-flow.md) for the two sale paths in detail, and
[Unit Conversion](unit-conversion.md) for how `stock_pieces` behaves for piece/bundle/grams
products.
