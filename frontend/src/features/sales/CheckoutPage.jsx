import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";

import { listProducts } from "../../api/products";
import { createSale, uploadSaleProof } from "../../api/sales";
import ActionBar from "../../components/ActionBar";
import AppLayout from "../../components/AppLayout";
import EmptyState from "../../components/EmptyState";
import LoadingState from "../../components/LoadingState";
import SegmentedControl from "../../components/SegmentedControl";
import { centsToPeso, isMeasured, lineTotalCents } from "../../lib/format";
import { sellerNavItems } from "../../lib/nav";
import { useAuth } from "../auth/AuthContext";
import CartLineItem from "./CartLineItem";
import CheckoutSummary from "./CheckoutSummary";
import OrderApproval from "./OrderApproval";
import PaymentSheet from "./PaymentSheet";
import ProductPickTile from "./ProductPickTile";
import QuantityPadSheet from "./QuantityPadSheet";
import { formatShortTimestamp, saleLineUnit, saleQuantityLabel, saleUnitLabel } from "./salesFormat";
import styles from "./sales.module.css";
import SalesHistoryRow from "./SalesHistoryRow";
import { usePendingOrders } from "./usePendingOrders";

// Picker tab for products that have no category.
const UNCATEGORIZED = "__none__";

// One cart line per product and sell mode, so a bundle product can have a bundle line and a by-piece line.
function cartKey(productId, byPiece) {
  return `${productId}:${byPiece ? "piece" : "unit"}`;
}

export default function CheckoutPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { t } = useAuth();

  // Walk-in rings up a sale; Buyer Account only approves buyers' online orders (?path=account&order=<id>).
  const [searchParams, setSearchParams] = useSearchParams();
  const checkoutPath = searchParams.get("path") === "account" ? "account" : "walkin";
  const reviewOrderId = checkoutPath === "account" ? searchParams.get("order") : null;
  const { data: pendingData, isLoading: isLoadingPending, isError: isPendingError } = usePendingOrders();
  const pendingOrders = pendingData?.items || [];

  const [view, setView] = useState("checkout");
  const [cart, setCart] = useState([]);
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [showPaymentSheet, setShowPaymentSheet] = useState(false);
  // The quantity keypad that is open: { productId, byPiece } (byPiece = the mode it opens in).
  const [pad, setPad] = useState(null);
  const [submitError, setSubmitError] = useState("");
  const [discountCents, setDiscountCents] = useState(0);
  // Category tab on the Add Items picker; "" = all products.
  const [pickCategory, setPickCategory] = useState("");

  const {
    data: productsData,
    isLoading: isLoadingProducts,
    isError: isProductsError,
  } = useQuery({
    queryKey: ["products", { forCheckout: true }],
    queryFn: () => listProducts({ pageSize: 100 }),
  });
  const products = useMemo(() => productsData?.items || [], [productsData]);
  const categories = useMemo(
    () => Array.from(new Set(products.map((p) => p.category).filter(Boolean))).sort(),
    [products],
  );
  const hasUncategorized = products.some((p) => !p.category);
  // Fall back to All if the chosen category no longer exists (e.g. after a refetch).
  const activeCategory =
    categories.includes(pickCategory) || (pickCategory === UNCATEGORIZED && hasUncategorized) ? pickCategory : "";
  const visibleProducts = !activeCategory
    ? products
    : products.filter((p) => (activeCategory === UNCATEGORIZED ? !p.category : p.category === activeCategory));
  const categoryTabs = [
    { value: "", label: t("checkout.allCategories") },
    ...categories.map((category) => ({ value: category, label: category })),
    ...(hasUncategorized ? [{ value: UNCATEGORIZED, label: t("checkout.uncategorized") }] : []),
  ];

  const cartRows = cart
    .map((entry) => {
      const product = products.find((p) => p.id === entry.productId);
      if (!product) return null;
      // A bundle product sold by the piece is its own line, priced per piece.
      const lineUnit = saleLineUnit(product, entry.byPiece);
      // A price the seller agreed for this sale only; null = the line's list price.
      const unitPriceCents = entry.unitPriceCents ?? lineUnit.priceCents;
      return {
        id: entry.key,
        productId: entry.productId,
        byPiece: entry.byPiece,
        name: product.name,
        listPriceCents: lineUnit.priceCents,
        costCents: lineUnit.costCents,
        unitPriceCents,
        priceUnitLabel: saleUnitLabel(lineUnit.unitType, lineUnit.unitLabel),
        quantityLabel: saleQuantityLabel(lineUnit.unitType, entry.quantity, lineUnit.unitLabel),
        steppable: !isMeasured(lineUnit.unitType),
        quantity: entry.quantity,
        lineTotalCents: lineTotalCents(unitPriceCents, entry.quantity, lineUnit.unitType),
      };
    })
    .filter(Boolean);

  const subtotalCents = cartRows.reduce((sum, row) => sum + row.lineTotalCents, 0);
  const hasCart = cart.length > 0;
  const canComplete = hasCart;

  function setCartQuantity(product, quantity, byPiece = false) {
    const key = cartKey(product.id, byPiece);
    setCart((current) => {
      const existing = current.find((entry) => entry.key === key);
      if (!quantity || quantity <= 0) return current.filter((entry) => entry.key !== key);
      if (existing) return current.map((entry) => (entry.key === key ? { ...entry, quantity } : entry));
      return [...current, { key, productId: product.id, byPiece, quantity, unitPriceCents: null }];
    });
  }

  function changeQuantity(key, delta) {
    setCart((current) =>
      current
        .map((entry) => (entry.key === key ? { ...entry, quantity: entry.quantity + delta } : entry))
        .filter((entry) => entry.quantity > 0),
    );
  }

  function changePrice(key, unitPriceCents) {
    setCart((current) => current.map((entry) => (entry.key === key ? { ...entry, unitPriceCents } : entry)));
  }

  function cartQuantity(productId, byPiece) {
    return cart.find((entry) => entry.key === cartKey(productId, byPiece))?.quantity || 0;
  }

  // From a picker tile: open on the bundle line unless only a by-piece line is in the cart.
  function openPadForProduct(productId) {
    setPad({ productId, byPiece: !cartQuantity(productId, false) && cartQuantity(productId, true) > 0 });
  }

  const padProduct = pad && products.find((p) => p.id === pad.productId);
  const quantityPad = padProduct && (
    <QuantityPadSheet
      product={padProduct}
      initialByPiece={pad.byPiece}
      quantityFor={(byPiece) => cartQuantity(padProduct.id, byPiece)}
      onConfirm={(quantity, byPiece) => {
        setCartQuantity(padProduct, quantity, byPiece);
        setPad(null);
      }}
      onClose={() => setPad(null)}
    />
  );

  const createSaleMutation = useMutation({
    // The sale is saved (and stock deducted) first; a failed photo upload never undoes or retries it.
    mutationFn: async ({ payload, proofFile }) => {
      const sale = await createSale(payload);
      if (!proofFile) return { sale, proofFailed: false };
      try {
        return { sale: await uploadSaleProof(sale.id, proofFile), proofFailed: false };
      } catch {
        return { sale, proofFailed: true };
      }
    },
    onSuccess: ({ sale, proofFailed }) => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["lowStockProducts"] });
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      queryClient.invalidateQueries({ predicate: (query) => String(query.queryKey[0]).startsWith("analytics") });
      navigate(`/sales/${sale.id}/receipt`, { replace: true, state: proofFailed ? { proofFailed: true } : undefined });
    },
    onError: (err) => {
      setSubmitError(err.response?.data?.detail || "Could not complete the sale.");
    },
  });

  function openPaymentSheet() {
    if (!canComplete) return;
    setSubmitError("");
    setShowPaymentSheet(true);
  }

  function completeSale(proofFile) {
    if (!canComplete || createSaleMutation.isPending) return;
    setSubmitError("");
    createSaleMutation.mutate({
      payload: {
        saleType: "walk_in",
        paymentMethod,
        items: cart.map((entry) => ({
          productId: entry.productId,
          quantity: entry.quantity,
          unitPriceCents: entry.unitPriceCents ?? undefined,
          byPiece: entry.byPiece || undefined,
        })),
        discountCents: discountCents || undefined,
      },
      proofFile: paymentMethod === "cash" ? null : proofFile,
    });
  }

  if (view === "pick") {
    return (
      <AppLayout navItems={sellerNavItems()} title="Add Items" backTo={() => setView("checkout")} hideBottomNav>
        <div className={styles["pick-page"]}>
          {isLoadingProducts && <LoadingState message="Loading products…" />}
          {isProductsError && <EmptyState message="Could not load products." />}
          {!isLoadingProducts && !isProductsError && products.length === 0 && (
            <EmptyState message="No products yet — add products to your inventory first." />
          )}
          {categories.length > 0 && (
            <div className={styles.chips} role="tablist">
              {categoryTabs.map((tab) => (
                <button
                  key={tab.value || "all"}
                  type="button"
                  role="tab"
                  aria-selected={activeCategory === tab.value}
                  className={`${styles.chip} ${activeCategory === tab.value ? styles["chip-active"] : ""}`}
                  onClick={() => setPickCategory(tab.value)}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          )}
          <div className={styles["pick-grid"]}>
            {visibleProducts.map((product) => (
              <ProductPickTile
                key={product.id}
                product={product}
                cartLines={cart.filter((entry) => entry.productId === product.id)}
                onOpenAmount={() => openPadForProduct(product.id)}
              />
            ))}
          </div>
          <ActionBar>
            <button type="button" className={styles["done-button"]} onClick={() => setView("checkout")}>
              {hasCart
                ? `Done · ${cart.length} item${cart.length === 1 ? "" : "s"} · ${centsToPeso(subtotalCents)}`
                : "Done"}
            </button>
          </ActionBar>
        </div>
        {quantityPad}
      </AppLayout>
    );
  }

  return (
    <AppLayout navItems={sellerNavItems()} title="New Sale">
      <div className={styles.checkout}>
        <div className={styles["checkout-main"]}>
          <div className={styles["checkout-path"]}>
            <SegmentedControl
              options={[
                { value: "walkin", label: t("checkout.walkIn") },
                {
                  value: "account",
                  label: pendingOrders.length
                    ? `${t("checkout.buyerAccount")} (${pendingOrders.length})`
                    : t("checkout.buyerAccount"),
                },
              ]}
              value={checkoutPath}
              onChange={(value) => {
                setSearchParams(value === "account" ? { path: "account" } : {}, { replace: true });
                setSubmitError("");
              }}
            />
          </div>

          {reviewOrderId && (
            <div className={styles["orders-list"]}>
              <button
                type="button"
                className={styles["order-back"]}
                onClick={() => setSearchParams({ path: "account" }, { replace: true })}
              >
                ← {t("orders.allPending")}
              </button>
              <OrderApproval
                key={reviewOrderId}
                saleId={reviewOrderId}
                onApproved={(sale) => navigate(`/sales/${sale.id}/receipt`, { replace: true })}
                onRejected={() => setSearchParams({ path: "account" }, { replace: true })}
              />
            </div>
          )}

          {checkoutPath === "account" && !reviewOrderId && (
            <div className={styles["orders-list"]}>
              <p className={styles.hint}>{t("orders.buyerAccountHint")}</p>
              {isLoadingPending && <LoadingState message={t("orders.loading")} />}
              {isPendingError && <EmptyState message={t("orders.loadError")} />}
              {pendingData && pendingOrders.length === 0 && <EmptyState message={t("orders.empty")} />}
              {pendingOrders.map((order) => (
                <SalesHistoryRow
                  key={order.id}
                  showTag={false}
                  sale={{
                    saleType: order.saleType,
                    status: order.status,
                    title: order.buyerName || "Buyer",
                    amountCents: order.totalCents,
                    itemsSummary: order.paymentProofUrl
                      ? t("orders.proofTitle")
                      : order.paymentMethod === "cash"
                        ? t("orders.sellerCashHint")
                        : t("orders.noProof"),
                    timeLabel: formatShortTimestamp(order.createdAt),
                  }}
                  onClick={() => setSearchParams({ path: "account", order: order.id }, { replace: true })}
                />
              ))}
            </div>
          )}

          {checkoutPath === "walkin" && (
            <>
              <p className={styles.hint}>Log the sale — no account needed</p>
              <div>
                <div className={styles["cart-heading"]}>Cart</div>
                <button type="button" className={styles["add-items-button"]} onClick={() => setView("pick")}>
                  + Add Items
                </button>
                {hasCart ? (
                  <div className={styles["cart-list"]}>
                    {cartRows.map((row) => (
                      <CartLineItem
                        key={row.id}
                        item={row}
                        onIncrement={() => changeQuantity(row.id, 1)}
                        onDecrement={() => changeQuantity(row.id, -1)}
                        onQuantityClick={() => setPad({ productId: row.productId, byPiece: row.byPiece })}
                        onPriceChange={(cents) => changePrice(row.id, cents)}
                      />
                    ))}
                  </div>
                ) : (
                  <EmptyState message="No items yet — add items to this sale" />
                )}
              </div>
            </>
          )}
        </div>

        {checkoutPath === "walkin" && (
          <CheckoutSummary
            subtotalCents={subtotalCents}
            discountCents={discountCents}
            onDiscountChange={hasCart ? setDiscountCents : undefined}
            disabled={!canComplete || createSaleMutation.isPending}
            onCompleteSale={openPaymentSheet}
          />
        )}
      </div>

      {quantityPad}

      {showPaymentSheet && (
        <PaymentSheet
          totalCents={subtotalCents}
          paymentMethod={paymentMethod}
          onPaymentMethodChange={setPaymentMethod}
          onConfirm={completeSale}
          onClose={() => setShowPaymentSheet(false)}
          isSubmitting={createSaleMutation.isPending}
          error={submitError}
        />
      )}
    </AppLayout>
  );
}
