import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import { listProducts, searchProductsByImage } from "../../api/products";
import AppLayout from "../../components/AppLayout";
import EmptyState from "../../components/EmptyState";
import IconButton from "../../components/IconButton";
import ImageSearchPanel from "../../components/ImageSearchPanel";
import LoadingState from "../../components/LoadingState";
import SearchField from "../../components/SearchField";
import SegmentedControl from "../../components/SegmentedControl";
import { sellerNavItems } from "../../lib/nav";
import { flushQuickSellQueue, queueLength } from "../../lib/offlineQueue";
import styles from "./inventory.module.css";
import ProductListItem from "./ProductListItem";
import RestockPicker from "./RestockPicker";

const STOCK_FILTERS = [
  { value: "", label: "All" },
  { value: "in_stock", label: "In Stock" },
  { value: "low", label: "Low" },
  { value: "out", label: "Out" },
];

export default function InventoryPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [stockStatus, setStockStatus] = useState("");
  const [page, setPage] = useState(1);
  const location = useLocation();
  // Analytics links here with { view: "restock" } to open the restock picker directly.
  const [view, setView] = useState(() => (location.state?.view === "restock" ? "restock" : "list"));
  const [queuedCount, setQueuedCount] = useState(() => queueLength());
  const [showImageSearch, setShowImageSearch] = useState(false);
  const [imageSearch, setImageSearch] = useState(null); // { query, products }
  const [imageSearchError, setImageSearchError] = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["products", { search: query, stockStatus, page }],
    queryFn: () => listProducts({ search: query, stockStatus, page, pageSize: 24 }),
    placeholderData: (previous) => previous,
    enabled: !imageSearch,
  });

  const imageSearchMutation = useMutation({
    mutationFn: searchProductsByImage,
    onSuccess: (result) => {
      setImageSearch({ query: result.query, products: result.results.map((r) => r.product) });
      setShowImageSearch(false);
      setImageSearchError("");
    },
    onError: (err) => {
      setImageSearchError(err.response?.data?.detail || "Could not search by photo. Try again.");
    },
  });

  async function syncQueuedSales() {
    const { flushed, remaining } = await flushQuickSellQueue();
    setQueuedCount(remaining);
    if (flushed > 0) {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["lowStockProducts"] });
    }
  }

  useEffect(() => {
    syncQueuedSales();
    window.addEventListener("online", syncQueuedSales);
    return () => window.removeEventListener("online", syncQueuedSales);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const items = imageSearch ? imageSearch.products : data?.items || [];
  const totalPages = !imageSearch && data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;

  if (view === "restock") {
    return (
      <AppLayout navItems={sellerNavItems()} title="Restock Items" backTo={() => setView("list")} hideBottomNav>
        <RestockPicker onDone={() => setView("list")} />
      </AppLayout>
    );
  }

  return (
    <AppLayout navItems={sellerNavItems()} title="Inventory">
      <div className={styles.page}>
        <div className={styles.toolbar}>
          <SearchField
            value={query}
            onChange={(value) => {
              setQuery(value);
              setPage(1);
              setImageSearch(null);
            }}
            placeholder="Search products"
          />
          <IconButton icon="camera" label="Search by photo" onClick={() => setShowImageSearch(true)} />
        </div>

        {showImageSearch && (
          <ImageSearchPanel
            hint="Snap or upload a photo, then tell us what it is — we'll find it in your stock."
            isSubmitting={imageSearchMutation.isPending}
            error={imageSearchError}
            onClose={() => setShowImageSearch(false)}
            onSubmit={(file, text) => {
              setImageSearchError("");
              imageSearchMutation.mutate({ file, query: text });
            }}
          />
        )}

        {imageSearch ? (
          <div className={styles["active-filter"]}>
            <span>Photo search: "{imageSearch.query}"</span>
            <button type="button" onClick={() => setImageSearch(null)}>
              Clear
            </button>
          </div>
        ) : (
          <div className={styles.toolbar}>
            <SegmentedControl
              options={STOCK_FILTERS}
              value={stockStatus}
              onChange={(value) => {
                setStockStatus(value);
                setPage(1);
              }}
            />
          </div>
        )}

        <div className={styles["add-actions"]}>
          <button type="button" className={styles["add-button"]} onClick={() => navigate("/inventory/new")}>
            + Add Product
          </button>
          <button type="button" className={styles["add-button"]} onClick={() => setView("restock")}>
            + Restock Items
          </button>
        </div>

        {queuedCount > 0 && (
          <div className={styles["queue-banner"]} role="status">
            {queuedCount} sale{queuedCount === 1 ? "" : "s"} pending sync — will send automatically when you're back online.
          </div>
        )}

        {!imageSearch && isLoading && <LoadingState message="Loading products…" />}
        {!imageSearch && isError && <EmptyState message="Could not load products." />}
        {(imageSearch || (!isLoading && !isError)) && items.length === 0 && (
          <EmptyState message={imageSearch ? "No matches for that photo search." : "No products found."} />
        )}

        <div className={styles.grid}>
          {items.map((product) => (
            <ProductListItem key={product.id} product={product} />
          ))}
        </div>

        {totalPages > 1 && (
          <div className={styles.pagination}>
            <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Previous
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Next
            </button>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
