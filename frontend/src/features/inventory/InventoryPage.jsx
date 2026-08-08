import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { listProducts, quickSellProduct } from "../../api/products";
import AppLayout from "../../components/AppLayout";
import EmptyState from "../../components/EmptyState";
import IconButton from "../../components/IconButton";
import LoadingState from "../../components/LoadingState";
import SearchField from "../../components/SearchField";
import SegmentedControl from "../../components/SegmentedControl";
import { sellerNavItems } from "../../lib/nav";
import { enqueueQuickSell, flushQuickSellQueue, isNetworkError, queueLength } from "../../lib/offlineQueue";
import styles from "./inventory.module.css";
import ProductListItem from "./ProductListItem";
import QuickSellSheet from "./QuickSellSheet";

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
  const [sellTarget, setSellTarget] = useState(null);
  const [sellError, setSellError] = useState("");
  const [queuedCount, setQueuedCount] = useState(() => queueLength());
  const [queuedNotice, setQueuedNotice] = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["products", { search: query, stockStatus, page }],
    queryFn: () => listProducts({ search: query, stockStatus, page, pageSize: 24 }),
    placeholderData: (previous) => previous,
  });

  async function syncQueuedSales() {
    const { flushed, remaining } = await flushQuickSellQueue();
    setQueuedCount(remaining);
    if (flushed > 0) {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["lowStockProducts"] });
    }
    if (remaining === 0) {
      setQueuedNotice("");
    }
  }

  useEffect(() => {
    syncQueuedSales();
    window.addEventListener("online", syncQueuedSales);
    return () => window.removeEventListener("online", syncQueuedSales);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const quickSellMutation = useMutation({
    mutationFn: async ({ id, payload }) => {
      try {
        return await quickSellProduct(id, payload);
      } catch (err) {
        if (isNetworkError(err)) {
          const newCount = enqueueQuickSell({ id, payload });
          setQueuedCount(newCount);
          return { queued: true };
        }
        throw err;
      }
    },
    onMutate: async ({ id, payload }) => {
      setSellError("");
      await queryClient.cancelQueries({ queryKey: ["products"] });
      const previous = queryClient.getQueriesData({ queryKey: ["products"] });

      queryClient.setQueriesData({ queryKey: ["products"] }, (current) => {
        if (!current) return current;
        return {
          ...current,
          items: current.items.map((item) =>
            item.id === id
              ? { ...item, stockPieces: item.stockPieces - payload.quantity * item.piecesPerUnit }
              : item,
          ),
        };
      });

      return { previous };
    },
    onError: (err, _vars, context) => {
      context?.previous?.forEach(([key, value]) => queryClient.setQueryData(key, value));
      setSellError(err.response?.data?.detail || "Could not complete the sale.");
    },
    onSuccess: (result) => {
      setSellTarget(null);
      setQueuedNotice(result?.queued ? "You're offline — the sale was saved and will sync automatically." : "");
    },
    onSettled: (result) => {
      if (!result?.queued) {
        queryClient.invalidateQueries({ queryKey: ["products"] });
        queryClient.invalidateQueries({ queryKey: ["lowStockProducts"] });
      }
    },
  });

  const items = data?.items || [];
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;

  return (
    <AppLayout
      navItems={sellerNavItems()}
      title="Inventory"
      headerAction={<IconButton icon="plus" variant="primary" label="Add product" onClick={() => navigate("/inventory/new")} />}
    >
      <div className={styles.page}>
        <div className={styles.toolbar}>
          <SearchField
            value={query}
            onChange={(value) => {
              setQuery(value);
              setPage(1);
            }}
            placeholder="Search products"
          />
        </div>

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

        {queuedCount > 0 && (
          <div className={styles["queue-banner"]} role="status">
            {queuedCount} sale{queuedCount === 1 ? "" : "s"} pending sync — will send automatically when you're back online.
          </div>
        )}
        {queuedNotice && (
          <div className={styles["queue-banner"]} role="status">
            {queuedNotice}
          </div>
        )}

        {isLoading && <LoadingState message="Loading products…" />}
        {isError && <EmptyState message="Could not load products." />}
        {!isLoading && !isError && items.length === 0 && <EmptyState message="No products found." />}

        <div className={styles.grid}>
          {items.map((product) => (
            <ProductListItem key={product.id} product={product} onQuickSell={setSellTarget} />
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

      {sellTarget && (
        <QuickSellSheet
          product={sellTarget}
          isSubmitting={quickSellMutation.isPending}
          error={sellError}
          onClose={() => {
            setSellTarget(null);
            setSellError("");
          }}
          onConfirm={(payload) => quickSellMutation.mutate({ id: sellTarget.id, payload })}
        />
      )}
    </AppLayout>
  );
}
