# Deferred Features

Things that are stubbed, out-of-scope, or intentionally simplified in the current implementation
— called out here so they aren't mistaken for bugs.

## Payment gateway integration

`payment_method` (`cash | gcash | maya | bank_transfer | other`) is recorded on every sale, but
there is no integration with GCash, Maya, or any bank/card processor. Sellers list where they
get paid as [payout accounts](api/payouts-service.md) (account details plus a QR image), and
buyers pay outside the app. For a digital online order, the buyer uploads a screenshot of the
payment and the seller checks it by eye before tapping **Confirm payment**. Nothing in the
backend captures, verifies or reconciles the money itself.

## Real-time messaging

`app/routers/messages.py` is a plain REST API — there is no WebSocket, SSE, or push channel.
The frontend polls: `ConversationListPage` and `ChatPage` refetch every 6–8 seconds via TanStack
Query's `refetchInterval`. This is adequate for a low-frequency market-stall chat but is not
real-time delivery.

## Vision-based image search

`POST /catalog/search-by-image` (`app/routers/catalog.py`) and its seller-side twin
`POST /products/search-by-image` (`app/routers/inventory.py`) accept and validate an uploaded
photo (JPEG/PNG/WebP) but do not analyze it. The code comment in the router spells out the intent:

> Stage 1: the photo is accepted but not analyzed — it's a shortcut into a pre-filled text search
> the buyer confirms. Stage 2 swaps this matching step for real vision search without changing the
> request/response shape.

Today both run a keyword search on the `query` form field and return those results with
`confidence: null` on every item — the photo itself has no effect on the results.

## Multi-staff accounts

Each `User` row with `role = seller` has exactly one `SellerProfile` (a single stall/business
identity). There is no concept of multiple staff logins under one stall, staff permission tiers,
or an owner/employee distinction — whoever holds the seller account's credentials has full access
to that stall's inventory, sales, and messages.

## Full offline-first sync

`frontend/src/lib/offlineQueue.js` provides partial resilience, not full offline-first support: it
queues **quick-sell** requests in `localStorage` when a request fails with a network error (no
response reaching the server — not a rejection like insufficient stock), and replays them on
reconnect, stopping at the first entry that still fails on the network but dropping entries the
server actively rejects. Browsing, checkout, approving orders, messaging, and every other action
still require a live connection — there is no general offline cache or conflict-resolution layer.

The queue currently gets no new entries: the quick-sell screen (`QuickSellSheet.jsx`) isn't
mounted anywhere and nothing calls `enqueueQuickSell`. `InventoryPage` still replays any queued
entries when it loads and when the browser comes back online. Walk-in sales made through the New
Sale cart are not queued at all.
