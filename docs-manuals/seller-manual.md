# Public Market POS — Seller Manual

Welcome to Public Market POS. This guide walks through everyday selling tasks: setting up your
stall, managing inventory, ringing up sales, approving online orders, and reviewing what you've
sold.

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

Next you'll see **How should buyers pay you?** Add your GCash, Maya or bank account and its QR
code (see [1.4](#14-payout-accounts-how-buyers-pay-you)), then tap **Save & continue**, or tap
**Skip for now** to do it later. You'll then land on your **Home** dashboard.

## 1.2 Logging In

1. Enter your **Email** and **Password** on the sign-in screen.
2. Tap **Sign In**.

**Logging in with a QR code (optional).** You can make a personal login QR so you don't have to
type your email and password:

1. Go to **Profile** → **Login QR** → **Create login QR**, and enter your password.
2. Tap **Download QR image** and keep the picture somewhere safe. It is shown only once.
3. Next time, on the login screen tap **Log in with QR code**, then point the camera at the QR or
   tap **Upload QR image** to choose the saved picture.

> Anyone who has your login QR can log in as you, so treat it like a password. Changing your
> password does **not** stop the QR from working. To make an old QR stop working, go to Profile and
> tap **Regenerate login QR** (makes a new one) or **Revoke login QR**.

## 1.3 Editing Your Stall Details Later

Your stall setup isn't locked in at registration — you can update it anytime:

1. Open **Profile** from the navigation.
2. Edit **Full name**, **Phone**, **Business name**, **Business type**, **Address**, or
   **Description**.
3. Tap **Save Changes**.

> Note: Your email is shown but cannot be changed from this screen.

The Profile screen is also where you switch the language (**English** / **Tagalog**), turn
**Dark mode** on or off, and log out.

## 1.4 Payout Accounts (How Buyers Pay You)

Payout accounts tell buyers where to send money when they don't pay in cash.

1. Open **Profile** and scroll to **Payout accounts**.
2. Tap **Add payout account**.
3. Choose the **Payment method**: **GCash**, **Maya**, **Bank**, or **Other**.
4. Fill in **Account name** and **Account / mobile number**. For **Bank**, also enter the **Bank
   name**. For **Other**, enter the **Provider name** (e.g. GoTyme, ShopeePay).
5. Tap **Save account**.
6. Tap **Tap to add your QR code** and pick a photo of your QR.

![Screenshot: payout accounts on the Profile screen](placeholder.png)

Your first account becomes your **Default** one. Tap **Make default** on another account to
switch, or use **Edit** and **Delete** to manage your accounts.

> Note: Buyers can only choose GCash, Maya, Bank or Other if you have an account for that
> method. Cash is always available. Until you add an account, your Home dashboard shows a
> reminder.

## 1.5 Your Home Dashboard

**Home** shows today's numbers at a glance: **Today's Sales**, **Today's Revenue**, low-stock
items and your **Top Seller**, plus a sales trend chart. Tap **Customize** to choose which cards
are pinned to the top, then tap **Done**.

Banners at the top tell you when something needs attention: online orders waiting for your
approval, items running low, or missing payout accounts. Tap the orders banner to go straight to
them.

---

# 2. Managing Inventory

## 2.1 Adding a Product

1. Open **Inventory** from the navigation.
2. Tap **+ Add Product**.
3. Fill in the product form:
   - Tap the photo area to **add a photo** (JPEG, PNG, or WebP)
   - **Product Name**
   - **Price (₱)**
   - **Cost price (₱)** (optional) — what one unit costs you. The app uses it to show your
     profit and margin in **Analytics**, and shows the margin at your current price as you type.
   - **Category** (optional) — pick an existing category, search for one, or type a new name
     and tap **Add new category**
   - **Unit Type** — choose **Per Piece**, **Bundle**, or **Per Unit**
   - If you chose **Bundle**, a **Pieces per Bundle** field appears; if you chose **Per Unit**, a
     **Unit of Measure** picker appears (see 2.2 below)
   - **Starting Stock** (in pieces, or in your chosen unit for **Per Unit** products)
   - **Low Stock Threshold** — how low stock can get before it's flagged
   - **Description** (optional)
4. Tap **Save Product**.

![Screenshot: add product form](placeholder.png)

> Note: To remove a category you no longer use, open the **Category** picker and tap **Delete
> category** next to it. Products that used it become uncategorized; nothing else changes.

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

  A bundle product can also be **sold per piece** (*tingi*). On **New Sale → Add Items** the
  product shows *"Can also be sold per piece"*; tap it and switch the keypad from **Bundle** to
  **Per piece**. One piece costs the bundle price ÷ pieces per bundle (₱50 bundle of 10 → ₱5 each),
  and you can still change the price in the cart. Buyers get the same choice when they order online.
  Selling 3 pieces deducts exactly 3 pieces, so stock may show as e.g. **7 bundles + 22 pc**.

- **Per Unit** — priced and sold by a measurement you choose: tap a preset (**kg**, **g**, **m**,
  **cm**, **ft**, **yd**, **L**) or type your own (e.g. `sack`, `gallon`). The **Price** is per one
  whole unit (e.g. ₱120 per yd), and you can sell, restock, and set stock in fractions up to 3
  decimals — `1.5` yd, `0.25` kg.

## 2.3 Editing a Product

1. From **Inventory**, tap any product row to open it.
2. Change any field and tap **Save Changes**.

> Note: Starting stock can't be edited directly from here — use **Restock** (below) or a sale to
> change stock, so every change is recorded. Changing the **Cost price** only affects future
> sales; profit on past sales stays as it was.

## 2.4 Restocking

**One product:**

1. Open the product from **Inventory**.
2. In the **Restock** section, enter **Pieces to add** (or the amount in the product's unit,
   e.g. `2.5` kg, for **Per Unit** products).
3. Tap **Add Stock**.

**Several products from one delivery:**

1. On **Inventory**, tap **+ Restock Items**.
2. Find each product you received (use the search box) and enter how much arrived.
3. If the price you paid has changed, enter the new **Cost per unit** for that product
   (optional).
4. Tap **Save Restock**. The button shows how many products you're restocking.

## 2.5 Finding Products

- Type in **Search products** to search by name.
- Use the **All / In Stock / Low / Out** filter to see only products in that stock state.
- Tap the **camera icon** to **search by photo**: snap or pick a photo, type what it is, and
  search. Results come from the description you type; the photo itself isn't analyzed yet. Tap
  **Clear** to go back to your full list.

## 2.6 Low Stock Alerts

Products at or below their **Low Stock Threshold** show a **Low Stock** badge in Inventory and
appear on your **Home** dashboard, so you know what to reorder before it runs out.

---

# 3. Ringing Up a Sale

The **New Sale** screen (the **Sell** button in the middle of the bottom bar on phones) has two
tabs:

- **Walk-in Sale** — for customers at your stall. Nothing is linked to a buyer account.
- **Buyer Account** — online orders that buyers placed in the app and that are waiting for your
  approval (see [3.3](#33-approving-online-orders)). You don't add items here.

## 3.1 Walk-in Sale

1. Open **New Sale**. It starts on **Walk-in Sale**.
2. Tap **+ Add Items**, then tap a product tile to open the number pad (see
   [4. Manual Stock Deduction](#4-manual-stock-deduction)). Use the category chips at the top to
   narrow the list.
3. Tap **Done** to go back to the cart.
4. Check the cart. If you agreed on a different price for an item, open its price and change the
   **Unit price** for this sale only (tap **Reset** to go back to your list price). The app warns
   you if the price is **Below your cost**. Your product's own price doesn't change.
5. To take money off the whole sale, enter a **Discount** and tap **Add**. The **Total** updates.
6. Tap **Complete Sale**.
7. Under **How did the buyer pay?**, choose **Cash** or one of your payout methods. For a digital
   payment, your matching QR code appears so the customer can scan it.
8. Tap **Confirm & Complete Sale**. For a digital payment with a QR, the QR first fills the
   screen so the customer can scan it easily. After they pay, you can tap **📷 Take photo of payment
   receipt** to snap the confirmation on their phone (optional; tap × to remove it or take it again).
   Once you've been paid, tap **Paid — Complete Sale** (or **Back to sale** to change the method).
9. You'll land on the **Receipt** screen with a QR code the buyer can scan. The payment photo is
   shown there for you only, never on the buyer's receipt. If you skipped it, or it didn't upload,
   tap **📷 Add payment photo**.

![Screenshot: New Sale cart and payment sheet](placeholder.png)

## 3.2 Payment Methods

Every sale records how it was paid: **Cash**, **GCash**, **Maya**, **Bank** or **Other**. Methods
you have no payout account for are greyed out. Add one under **Profile → Payout accounts** (see
[1.4](#14-payout-accounts-how-buyers-pay-you)).

> Note: The app only records the payment method. It doesn't move money or check that a digital
> payment arrived, so confirm it in your GCash, Maya or bank app first.

## 3.3 Approving Online Orders

When a buyer orders from your stall in the app, their items are held from your stock straight
away, but the order doesn't count as a sale until you approve it.

You'll know an order is waiting in three ways:

- A banner on **Home**, e.g. **"1 order is waiting for payment confirmation"**.
- A number on the **Buyer Account** tab, e.g. **Buyer Account (2)**.
- An order card in **Messages**, sent from the buyer: for a cash order, as soon as they place it;
  for a digital payment, each time they upload a payment screenshot. Tap **Review & approve**.

To approve or reject an order:

1. Open **New Sale → Buyer Account** and tap the order (or follow the banner or chat card).
2. GCash, Maya and bank orders show the buyer's **Payment screenshot**. Tap it to view it full
   size and check it against your account. Cash orders have no screenshot — approve them once
   the buyer pays you.
3. Tap **Approve order** once you've received the money. The order becomes a completed sale,
   counts in Transactions and Analytics under the buyer's name, and you'll see its receipt.
4. If the payment never arrived, tap **Reject order** (you can add a reason). The held items go
   back into your stock.

Tap **← All orders to approve** to go back to the list.

> Note: On a digital-payment order, **Approve order** stays disabled until the buyer uploads a
> screenshot. Orders waiting for approval don't count in your sales totals. The buyer can also
> cancel an order while it's waiting; its items then go back into your stock.

## 3.4 Voiding or Refunding a Sale

Open the sale's receipt (from **Transactions**, or right after completing it).

- **Void sale** — for a sale entered by mistake (wrong item, rang up twice). The sale is removed
  from your reports and its items go back into stock.
- **Refund sale** — for when the buyer returns the items. The amount is recorded as a refund and
  the items go back into stock.

Both ask for an optional reason. Either way the receipt stays in your records, labelled
**Voided** or **Refunded**. Partial refunds aren't supported.

---

# 4. Manual Stock Deduction

There is **no barcode scanner** in this app — every sale is entered by tapping, and stock is
deducted automatically based on what you tap and enter. There's nothing extra to do to "deduct
stock" — it happens as part of completing a sale.

## 4.1 Adding Items

1. On the item-picker screen (**+ Add Items** in New Sale), tap a product tile (**Tap to enter
   amount**).
2. Enter the quantity on the number pad — in pieces or bundles, or in the product's unit for a
   **Per Unit** item (use the decimal point for amounts like `1.5` yd or `0.25` kg).
3. Check the **Subtotal** shown, then tap **Add to Cart**.
4. To change an item already in the cart, tap its tile again and tap **Update Cart**, or
   **Remove from Cart**.

Stock for that product is reduced by exactly the amount you enter when you complete the sale.

## 4.2 What Happens If Stock Runs Out Mid-Sale

If a cart has multiple items and one of them doesn't have enough stock, the whole sale is
rejected — none of the items are deducted and no sale is recorded. You'll see an error message;
adjust the quantity or remove the item and try **Complete Sale** again.

---

# 5. Transactions

1. Open **Transactions** from the navigation.
2. Choose a date range: **Today**, **7 Days**, **30 Days**, or **Custom** (pick a **From** and
   **To** date).
3. Tap any sale to open its receipt, where you can void or refund it (see
   [3.4](#34-voiding-or-refunding-a-sale)).

To get rid of a test sale or a duplicate, use **Delete transaction** on its row. This voids the
sale: its items go back into stock and it drops out of your reports, but it stays in the list
marked **Voided**.

---

# 6. Analytics

Open **Analytics** from the navigation. At the top, **Insights** points out things worth acting
on, marked **Urgent**, **Check** or **FYI** — for example an item about to run out, a product
sold below its cost, a product with no cost price, or a sudden jump or drop in sales. Each
insight suggests what to do, such as **Restock now** or **Add its cost price**.

Below that are four tabs:

- **Sales** — net sales, number of sales, units sold and the average sale for the date range you
  pick, compared with the period before. Also your top 5 products and your average sales by
  weekday and by hour.
- **Profit** — gross profit, gross margin and cost of goods. **From sales to profit** shows how
  your gross sales at list price become net sales after price changes, discounts and refunds.
  Profit only covers products that have a **Cost price**; the tab tells you when some are
  missing.
- **Stock** — how many days of stock each product has left, what to reorder, and which items
  are slow-moving or overstocked.
- **Forecast** — expected sales for each product over the next 7 and 14 days, with the
  forecast's recent accuracy.

> Note: "Today" and every daily figure follow Philippine time. Voided sales, orders waiting for
> approval and cancelled orders never count.

---

# 7. Troubleshooting

**A product's stock looks wrong.**
Check the product's edit screen — if the number seems off, use **Restock** to correct it upward,
noting why in your own records. Every stock change (sales, restocks, voids, refunds, cancelled
orders) is logged internally, so a support request can trace exactly what happened to a
product's count.

**I tapped the wrong item during a sale.**
Before tapping **Complete Sale**, tap the item's tile again and change the amount, or tap
**Remove from Cart**. Nothing is deducted from stock until you complete the sale, so mistakes
made while building the cart cost nothing. If you already completed it, **void** the sale from
its receipt (see [3.4](#34-voiding-or-refunding-a-sale)).

**"Not enough stock" error when completing a sale.**
Someone else may have sold the last of that item first, an online order may be holding it, or
your cart quantity is more than you have. Lower the quantity to match what **Inventory** shows
as available, or remove the item.

**A payment method is greyed out.**
You don't have a payout account for that method yet. Add one under **Profile → Payout accounts**.

**I can't approve a GCash, Maya or bank order.**
The buyer hasn't uploaded a payment screenshot yet. Message them from the order's chat, or
reject the order if the payment isn't coming.

**I lost my connection while selling.**
Sales, order approvals and messages need an internet connection, and nothing is recorded until
it goes through. Once you're back online, check **Transactions** to see whether the sale was
saved before trying again, so it isn't recorded twice.
