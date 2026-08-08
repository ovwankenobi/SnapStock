import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { listProducts } from "../../api/products";
import { createSale, searchBuyers } from "../../api/sales";
import AppLayout from "../../components/AppLayout";
import EmptyState from "../../components/EmptyState";
import LoadingState from "../../components/LoadingState";
import SearchField from "../../components/SearchField";
import SegmentedControl from "../../components/SegmentedControl";
import { sellerNavItems } from "../../lib/nav";
import BuyerOptionRow from "./BuyerOptionRow";
import CartLineItem from "./CartLineItem";
import CheckoutSummary from "./CheckoutSummary";
import ProductPickTile from "./ProductPickTile";
import { saleQuantityLabel, saleUnitLabel } from "./salesFormat";
import styles from "./sales.module.css";
import SelectedBuyerBanner from "./SelectedBuyerBanner";
import WeighDialog from "./WeighDialog";

const PATH_OPTIONS = [
  { value: "walkin", label: "Walk-in Sale" },
  { value: "account", label: "Buyer Account" },
];
const PAYMENT_OPTIONS = [
  { value: "cash", label: "Cash" },
  { value: "gcash", label: "GCash" },
  { value: "maya", label: "Maya" },
];
const WEIGH_PRESETS = [250, 500, 1000];

export default function CheckoutPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [checkoutPath, setCheckoutPath] = useState("walkin");
  const [view, setView] = useState("checkout");
  const [selectedBuyer, setSelectedBuyer] = useState(null);
  const [buyerQuery, setBuyerQuery] = useState("");
  const [debouncedBuyerQuery, setDebouncedBuyerQuery] = useState("");
  const [cart, setCart] = useState([]);
  const [manualAmount, setManualAmount] = useState("");
  const [note, setNote] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [weighingProductId, setWeighingProductId] = useState(null);
  const [weighGrams, setWeighGrams] = useState("");
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedBuyerQuery(buyerQuery.trim()), 300);
    return () => clearTimeout(timer);
  }, [buyerQuery]);

  const {
    data: productsData,
    isLoading: isLoadingProducts,
    isError: isProductsError,
  } = useQuery({
    queryKey: ["products", { forCheckout: true }],
    queryFn: () => listProducts({ pageSize: 100 }),
  });
  const products = productsData?.items || [];

  const { data: buyerResults, isFetching: isSearchingBuyers } = useQuery({
    queryKey: ["buyerSearch", debouncedBuyerQuery],
    queryFn: () => searchBuyers(debouncedBuyerQuery),
    enabled: debouncedBuyerQuery.length >= 2,
  });

  const cartRows = cart
    .map((entry) => {
      const product = products.find((p) => p.id === entry.productId);
      if (!product) return null;
      return {
        id: entry.productId,
        name: product.name,
        unitPriceCents: product.priceCents,
        priceUnitLabel: saleUnitLabel(product.unitType),
        quantityLabel: saleQuantityLabel(product.unitType, entry.quantity),
        steppable: product.unitType !== "grams",
        quantity: entry.quantity,
        lineTotalCents: entry.quantity * product.priceCents,
      };
    })
    .filter(Boolean);

  const subtotalCents = cartRows.reduce((sum, row) => sum + row.lineTotalCents, 0);
  const hasCart = cart.length > 0;
  const manualAmountCents = Math.round(Number(manualAmount || 0) * 100);
  const canComplete =
    (checkoutPath === "account" && Boolean(selectedBuyer) && hasCart) ||
    (checkoutPath === "walkin" && (hasCart || manualAmountCents > 0));

  function setCartQuantity(product, quantity) {
    setCart((current) => {
      const without = current.filter((entry) => entry.productId !== product.id);
      if (!quantity || quantity <= 0) return without;
      return [...without, { productId: product.id, quantity }];
    });
  }

  function changeQuantity(productId, delta) {
    setCart((current) =>
      current
        .map((entry) => (entry.productId === productId ? { ...entry, quantity: entry.quantity + delta } : entry))
        .filter((entry) => entry.quantity > 0),
    );
  }

  const weighingProduct = products.find((p) => p.id === weighingProductId);

  const createSaleMutation = useMutation({
    mutationFn: createSale,
    onSuccess: (sale) => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["lowStockProducts"] });
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      navigate(`/sales/${sale.id}/receipt`, { replace: true });
    },
    onError: (err) => {
      setSubmitError(err.response?.data?.detail || "Could not complete the sale.");
    },
  });

  function completeSale() {
    if (!canComplete || createSaleMutation.isPending) return;
    setSubmitError("");
    createSaleMutation.mutate({
      saleType: checkoutPath === "account" ? "itemized" : "walk_in",
      buyerId: checkoutPath === "account" ? selectedBuyer.id : undefined,
      paymentMethod,
      items: cart.map((entry) => ({ productId: entry.productId, quantity: entry.quantity })),
      note: note.trim() || undefined,
      totalCents: hasCart ? undefined : manualAmountCents,
    });
  }

  if (view === "pick") {
    return (
      <AppLayout navItems={sellerNavItems()} title="Add Items">
        <div className={styles["pick-page"]}>
          {isLoadingProducts && <LoadingState message="Loading products…" />}
          {isProductsError && <EmptyState message="Could not load products." />}
          {!isLoadingProducts && !isProductsError && products.length === 0 && (
            <EmptyState message="No products yet — add products to your inventory first." />
          )}
          <div className={styles["pick-grid"]}>
            {products.map((product) => {
              const entry = cart.find((c) => c.productId === product.id);
              return (
                <ProductPickTile
                  key={product.id}
                  product={product}
                  cartQuantity={entry ? entry.quantity : 0}
                  onQuantityChange={(value) => setCartQuantity(product, Number(value))}
                  onOpenWeigh={() => {
                    setWeighingProductId(product.id);
                    setWeighGrams(entry ? String(entry.quantity) : "");
                  }}
                />
              );
            })}
          </div>
          <button type="button" className={styles["done-button"]} onClick={() => setView("checkout")}>
            Done
          </button>
        </div>
        {weighingProduct && (
          <WeighDialog
            product={weighingProduct}
            grams={weighGrams}
            onGramsChange={setWeighGrams}
            presets={WEIGH_PRESETS}
            onPresetSelect={(preset) => setWeighGrams(String(preset))}
            onConfirm={() => {
              setCartQuantity(weighingProduct, Number(weighGrams));
              setWeighingProductId(null);
            }}
            onClose={() => setWeighingProductId(null)}
          />
        )}
      </AppLayout>
    );
  }

  return (
    <AppLayout navItems={sellerNavItems()} title="New Sale">
      <div className={styles.checkout}>
        <div className={styles["checkout-main"]}>
          <div className={styles["checkout-path"]}>
            <SegmentedControl
              options={PATH_OPTIONS}
              value={checkoutPath}
              onChange={(value) => {
                setCheckoutPath(value);
                setSelectedBuyer(null);
                setSubmitError("");
              }}
            />
          </div>

          {checkoutPath === "account" && !selectedBuyer && (
            <div>
              <p className={styles.hint}>Search a buyer by phone or email</p>
              <SearchField value={buyerQuery} onChange={setBuyerQuery} placeholder="Search buyers..." />
              {debouncedBuyerQuery.length >= 2 && (
                <div className={styles["buyer-list"]}>
                  {!isSearchingBuyers && (buyerResults || []).length === 0 && (
                    <EmptyState message="No matching buyers." />
                  )}
                  {(buyerResults || []).map((buyer) => (
                    <BuyerOptionRow key={buyer.id} buyer={buyer} onSelect={setSelectedBuyer} />
                  ))}
                </div>
              )}
            </div>
          )}
          {selectedBuyer && <SelectedBuyerBanner buyer={selectedBuyer} onClear={() => setSelectedBuyer(null)} />}
          {checkoutPath === "walkin" && <p className={styles.hint}>Log the sale — no account needed</p>}

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
                  />
                ))}
              </div>
            ) : (
              <EmptyState message="No items yet — add items to this sale" />
            )}
          </div>

          {checkoutPath === "walkin" && !hasCart && (
            <div className={styles["manual-amount"]}>
              <div>
                <label className={styles["field-label"]} htmlFor="manual-amount-input">
                  Or just enter an amount
                </label>
                <input
                  id="manual-amount-input"
                  inputMode="numeric"
                  value={manualAmount}
                  onChange={(e) => setManualAmount(e.target.value.replace(/[^0-9]/g, ""))}
                  placeholder="₱0"
                />
              </div>
              <div>
                <label className={styles["field-label"]} htmlFor="sale-note-input">
                  Note (optional)
                </label>
                <input
                  id="sale-note-input"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="e.g. assorted vegetables"
                />
              </div>
            </div>
          )}

          <div className={styles["payment-section"]}>
            <div className={styles["field-label"]}>Payment Method</div>
            <SegmentedControl options={PAYMENT_OPTIONS} value={paymentMethod} onChange={setPaymentMethod} />
          </div>

          {submitError && <div className={styles["form-error"]}>{submitError}</div>}
        </div>

        <CheckoutSummary
          subtotalCents={hasCart ? subtotalCents : manualAmountCents}
          disabled={!canComplete || createSaleMutation.isPending}
          onCompleteSale={completeSale}
        />
      </div>
    </AppLayout>
  );
}
