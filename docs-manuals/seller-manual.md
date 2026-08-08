# Public Market POS — Seller Manual

Welcome to Public Market POS. This guide walks through everyday selling tasks: setting up your
stall, managing inventory, ringing up sales, and reviewing what you've sold.

> Note: Screens shown in this guide are placeholders. Replace them with real screenshots before
> distributing this manual.

---

# 1. Getting Started

## 1.1 Creating a Seller Account

1. On the sign-in screen, tap **Create Account**.
2. Choose **Seller** from the two role cards.
3. Fill in your details:
   - **Full Name**
   - **Email**
   - **Password** (at least 8 characters)
   - **Phone**
   - **Business Name** — your stall's name, shown to buyers
   - **Business Type** — choose **Retail**, **Wholesale**, or **Both**
   - **Address** (optional)
   - **Description** (optional) — a short blurb buyers see on your stall page
4. Tap **Create Account**.

![Screenshot: seller registration form](placeholder.png)

You'll be signed in automatically and taken to your **Home** dashboard.

## 1.2 Logging In

1. Enter your **Email** and **Password** on the sign-in screen.
2. Tap **Sign In**.

## 1.3 Editing Your Stall Details Later

Your stall setup isn't locked in at registration — you can update it anytime:

1. Open **Profile** from the bottom navigation.
2. Edit **Full name**, **Phone**, **Business name**, **Business type**, **Address**, or
   **Description**.
3. Tap **Save Changes**.

> Note: Your email is shown but cannot be changed from this screen.

---

# 2. Managing Inventory

## 2.1 Adding a Product

1. Open **Inventory** from the bottom navigation.
2. Tap the **+** button (top right).
3. Fill in the product form:
   - Tap the photo area to **add a photo** (JPEG, PNG, or WebP)
   - **Product Name**
   - **Price (₱)**
   - **Category** (optional — used for filtering)
   - **Unit Type** — choose **Per Piece**, **Bundle**, or **Per Kilo**
   - If you chose **Bundle** or **Per Kilo**, a second field appears (see 2.2 below)
   - **Starting Stock (pieces)**
   - **Low Stock Threshold** — how low stock can get before it's flagged
   - **Description** (optional)
4. Tap **Save Product**.

![Screenshot: add product form](placeholder.png)

## 2.2 Understanding Piece vs. Bundle

All stock is tracked internally as **pieces**, no matter how a product is sold — this keeps one
number as the source of truth even when you sell the same stock two different ways.

- **Per Piece** — one selling unit equals one piece. No conversion needed.
- **Bundle** — you set **Pieces per Bundle**. For example:

  > **1 bundle of pandesal = 25 pieces.**
  >
  > If you set **Pieces per Bundle** to `25` and start with **10 bundles**, you'd enter a
  > **Starting Stock** of `250` pieces. When you later sell 2 bundles, the app deducts
  > `2 × 25 = 50` pieces, leaving `200` pieces — shown to you as **8 bundles** remaining.

- **Per Kilo** — priced and sold by weight in grams (see [4. Manual Stock Deduction](#4-manual-stock-deduction)
  for how weighing works at checkout).

## 2.3 Editing a Product

1. From **Inventory**, tap any product row to open it.
2. Change any field and tap **Save Changes**.

> Note: Starting stock can't be edited directly from here — use **Restock** (below) or a sale to
> change stock, so every change is recorded.

## 2.4 Restocking

1. Open the product from **Inventory**.
2. Scroll to the **Restock** section.
3. Enter **Pieces to add**.
4. Tap **Add Stock**.

## 2.5 Low Stock Alerts

Products at or below their **Low Stock Threshold** show a **Low Stock** badge in Inventory and
appear in a banner on your **Home** dashboard, so you know what to reorder before it runs out.

---

# 3. Ringing Up a Sale

Public Market POS supports two kinds of sales from the same **New Sale** screen:

- **Walk-in Sale** — a cash-register-style sale with no buyer account. Nothing is linked to a
  buyer; it's just recorded against your stall.
- **Buyer Account** — a sale linked to a registered buyer (useful when a buyer wants a record of
  their purchase, or paid digitally through their account).

## 3.1 Walk-in Sale (Anonymous, Cash)

1. Open **New Sale** from the bottom navigation.
2. Leave the toggle on **Walk-in Sale**.
3. Tap **+ Add Items** and tap products to add them to the cart (see
   [4. Manual Stock Deduction](#4-manual-stock-deduction)), **or**, if you don't want to itemize,
   enter an amount directly under **Or just enter an amount** and add an optional **Note**.
4. Choose a **Payment Method** — **Cash**, **GCash**, or **Maya**.
5. Tap **Complete Sale**.
6. You'll land on the **Receipt** screen with a QR code you can **Share** or **Print**.

## 3.2 Buyer-Linked Sale

1. Open **New Sale** and switch the toggle to **Buyer Account**.
2. Search for the buyer by **phone or email**.
3. Tap the matching buyer from the results to select them.
4. Tap **+ Add Items** and build the cart as above.
5. Choose a **Payment Method** and tap **Complete Sale**.

> Note: A buyer-linked sale requires at least one item in the cart — you can't complete it with
> just a manual amount the way you can for a walk-in sale.

## 3.3 The Fastest Path: Quick Sell

For a single-item cash sale, you don't need the full **New Sale** screen:

1. On **Inventory**, find the product.
2. Tap the small **−1** button on its row.
3. Adjust the **quantity** with the stepper if selling more than one.
4. Choose a **Payment Method**.
5. Tap **Confirm Sale**.

This is the quickest way to log a sale while a customer is standing at your stall.

---

# 4. Manual Stock Deduction

There is **no barcode scanner** in this app — every sale is entered by tapping, and stock is
deducted automatically based on what you tap and enter. There's nothing extra to do to "deduct
stock" — it happens as part of completing a sale.

## 4.1 Adding Items by Piece or Bundle

1. From the item-picker screen (**+ Add Items** in New Sale), find the product tile.
2. Type the quantity directly into the number field on the tile (in pieces or bundles, matching
   how that product is sold).
3. Tap **Done** once you've added everything.

## 4.2 Adding a Weighed (Per Kilo) Item

1. On a **Per Kilo** product's tile, tap **Tap to enter weight**.
2. Enter the weight in **grams**, or tap a preset (**250g**, **500g**, **1kg**).
3. Confirm the **Subtotal** shown, then tap **Add to Cart**.

Stock for that product is reduced by exactly the number of grams you enter.

## 4.3 What Happens If Stock Runs Out Mid-Sale

If a cart has multiple items and one of them doesn't have enough stock, the whole sale is
rejected — none of the items are deducted and no sale is recorded. You'll see an error message;
adjust the quantity or remove the item and try **Complete Sale** again.

---

# 5. Viewing Sales History

1. Open **Sales History** from the bottom navigation (or **Home → Sales History**).
2. Use the **Today / This Week / This Month** filter to change the date range.
3. Tap any sale row to open its receipt.
4. The side panel shows a **demand forecast** — products likely to run low soon, based on your
   recent sales pace.

---

# 6. Troubleshooting

**A product's stock looks wrong.**
Check the product's edit screen — if the number seems off, use **Restock** to correct it upward,
noting why in your own records. Every stock change (sales, quick-sells, restocks) is logged
internally, so a support request can trace exactly what happened to a product's count.

**I tapped the wrong item during a sale.**
On the **New Sale** cart screen, use the **+/−** steppers on a cart line to adjust or zero out the
quantity before tapping **Complete Sale** — nothing is deducted from stock until you complete the
sale, so mistakes made while building the cart cost nothing.

**"Not enough stock" error when completing a sale.**
Someone else may have sold the last of that item first (or your cart quantity exceeds what's on
hand). Lower the quantity to match what **Inventory** shows as available, or remove the item.

**A quick-sell said "Sold" but I was offline.**
The app queues a quick-sell made while your phone has no connection and shows a banner (**"X
sale(s) pending sync"**). It automatically retries once you're back online — no action needed.
If the item sold out in the meantime, that queued sale is dropped rather than oversold, and it
will no longer appear as pending.

**A buyer isn't showing up in buyer search.**
Buyer search only matches by exact-ish **phone number or email**, and only finds buyers who
already created an account. If they haven't registered, ring the sale up as a **Walk-in Sale**
instead.
