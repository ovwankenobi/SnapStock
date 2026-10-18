import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { bulkRestockProducts, listProducts } from "../../api/products";
import ActionBar from "../../components/ActionBar";
import EmptyState from "../../components/EmptyState";
import LoadingState from "../../components/LoadingState";
import SearchField from "../../components/SearchField";
import styles from "./inventory.module.css";
import RestockPickTile from "./RestockPickTile";

export default function RestockPicker({ onDone }) {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [amounts, setAmounts] = useState({});
  const [costs, setCosts] = useState({});
  const [error, setError] = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["products", { forRestock: true }],
    queryFn: () => listProducts({ pageSize: 100 }),
  });
  const products = data?.items || [];
  const search = query.trim().toLowerCase();
  const visibleProducts = search ? products.filter((p) => p.name.toLowerCase().includes(search)) : products;

  const entries = Object.entries(amounts).filter(([, quantity]) => quantity > 0);

  const restockMutation = useMutation({
    mutationFn: bulkRestockProducts,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["lowStockProducts"] });
      queryClient.invalidateQueries({ predicate: (query) => String(query.queryKey[0]).startsWith("analytics") });
      onDone();
    },
    onError: (err) => {
      setError(err.response?.data?.detail || "Could not save the restock.");
    },
  });

  function saveRestock() {
    if (entries.length === 0 || restockMutation.isPending) return;
    setError("");
    restockMutation.mutate({
      items: entries.map(([productId, quantity]) => {
        const product = products.find((p) => p.id === productId);
        const unitCostCents = costs[productId];
        // Only send a cost the seller actually changed for this delivery.
        const changed = unitCostCents != null && unitCostCents !== product?.costCents;
        return { productId, quantity, unitCostCents: changed ? unitCostCents : undefined };
      }),
    });
  }

  return (
    <div className={styles["pick-page"]}>
      <div className={styles.toolbar}>
        <SearchField value={query} onChange={setQuery} placeholder="Search products" />
      </div>

      {isLoading && <LoadingState message="Loading products…" />}
      {isError && <EmptyState message="Could not load products." />}
      {!isLoading && !isError && visibleProducts.length === 0 && <EmptyState message="No products found." />}

      <div className={styles["pick-grid"]}>
        {visibleProducts.map((product) => (
          <RestockPickTile
            key={product.id}
            product={product}
            amount={amounts[product.id] || 0}
            onAmountChange={(quantity) => setAmounts((current) => ({ ...current, [product.id]: quantity }))}
            onCostChange={(cents) => setCosts((current) => ({ ...current, [product.id]: cents }))}
          />
        ))}
      </div>

      {error && <div className={styles["sheet-error"]}>{error}</div>}

      <ActionBar>
        <button
          type="button"
          className={styles["submit-button"]}
          disabled={entries.length === 0 || restockMutation.isPending}
          onClick={saveRestock}
        >
          {restockMutation.isPending ? "Saving..." : `Save Restock (${entries.length})`}
        </button>
        <button type="button" className={styles["cancel-button"]} onClick={onDone}>
          Cancel
        </button>
      </ActionBar>
    </div>
  );
}
