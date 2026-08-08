import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import {
  createProduct,
  getProduct,
  restockProduct,
  updateProduct,
  uploadProductPhoto,
} from "../../api/products";
import AppLayout from "../../components/AppLayout";
import EmptyState from "../../components/EmptyState";
import LoadingState from "../../components/LoadingState";
import { sellerNavItems } from "../../lib/nav";
import styles from "./inventory.module.css";
import ProductForm from "./ProductForm";

const EMPTY_DRAFT = {
  name: "",
  priceInput: "",
  unitType: "piece",
  piecesPerUnitInput: "1",
  stockInput: "0",
  lowStockThresholdInput: "10",
  category: "",
  description: "",
  photoUrl: null,
};

function draftFromProduct(product) {
  return {
    name: product.name,
    priceInput: String(Math.round(product.priceCents / 100)),
    unitType: product.unitType,
    piecesPerUnitInput: String(product.piecesPerUnit),
    stockInput: String(product.stockPieces),
    lowStockThresholdInput: String(product.lowStockThreshold),
    category: product.category || "",
    description: product.description || "",
    photoUrl: product.photoUrl,
  };
}

export default function ProductFormPage() {
  const { productId } = useParams();
  const isEditing = Boolean(productId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [restockAmount, setRestockAmount] = useState("");
  const [error, setError] = useState("");

  const {
    data: product,
    isLoading: isLoadingProduct,
    isError: isProductError,
  } = useQuery({
    queryKey: ["product", productId],
    queryFn: () => getProduct(productId),
    enabled: isEditing,
  });

  useEffect(() => {
    if (product) setDraft(draftFromProduct(product));
  }, [product]);

  function invalidateAndReturn() {
    queryClient.invalidateQueries({ queryKey: ["products"] });
    queryClient.invalidateQueries({ queryKey: ["lowStockProducts"] });
    navigate("/inventory");
  }

  const createMutation = useMutation({
    mutationFn: createProduct,
    onSuccess: invalidateAndReturn,
    onError: () => setError("Could not save product. Check the fields and try again."),
  });

  const updateMutation = useMutation({
    mutationFn: (payload) => updateProduct(productId, payload),
    onSuccess: invalidateAndReturn,
    onError: () => setError("Could not save changes. Check the fields and try again."),
  });

  const photoMutation = useMutation({
    mutationFn: (file) => uploadProductPhoto(productId, file),
    onSuccess: (updated) => {
      setDraft((current) => ({ ...current, photoUrl: updated.photoUrl }));
      queryClient.invalidateQueries({ queryKey: ["product", productId] });
    },
  });

  const restockMutation = useMutation({
    mutationFn: (quantity) => restockProduct(productId, { quantity }),
    onSuccess: (updated) => {
      setDraft((current) => ({ ...current, stockInput: String(updated.stockPieces) }));
      setRestockAmount("");
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["lowStockProducts"] });
    },
  });

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  function buildPayload() {
    const unitType = draft.unitType;
    return {
      name: draft.name.trim(),
      description: draft.description.trim() || null,
      priceCents: Number(draft.priceInput) * 100,
      unitType,
      piecesPerUnit: unitType === "piece" ? 1 : Number(draft.piecesPerUnitInput) || 1,
      lowStockThreshold: Number(draft.lowStockThresholdInput) || 0,
      category: draft.category.trim() || null,
    };
  }

  function handleSubmit() {
    setError("");
    if (!draft.name.trim() || !Number(draft.priceInput)) {
      setError("Name and price are required.");
      return;
    }

    if (isEditing) {
      updateMutation.mutate(buildPayload());
    } else {
      createMutation.mutate({ ...buildPayload(), stockPieces: Number(draft.stockInput) || 0 });
    }
  }

  function handlePhotoSelect(file) {
    if (isEditing) {
      photoMutation.mutate(file);
    } else {
      setError("Save the product first, then add a photo.");
    }
  }

  if (isEditing && isLoadingProduct) {
    return (
      <AppLayout navItems={sellerNavItems()} title="Edit Product">
        <div className={styles.page}>
          <LoadingState message="Loading product…" />
        </div>
      </AppLayout>
    );
  }

  if (isEditing && isProductError) {
    return (
      <AppLayout navItems={sellerNavItems()} title="Edit Product">
        <div className={styles.page}>
          <EmptyState message="Could not load this product." />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout navItems={sellerNavItems()} title={isEditing ? "Edit Product" : "Add Product"}>
      <div className={styles.page}>
        <ProductForm
          value={{ ...draft, disableStock: isEditing }}
          onFieldChange={(field, fieldValue) => setDraft((current) => ({ ...current, [field]: fieldValue }))}
          onSubmit={handleSubmit}
          onPhotoSelect={handlePhotoSelect}
          submitLabel={isEditing ? "Save Changes" : "Create Product"}
          isSubmitting={isSubmitting}
        />

        {error && <div className={styles["sheet-error"]}>{error}</div>}

        {isEditing && (
          <div className={styles["form-panel"]}>
            <div className={styles["field-label"]}>Restock</div>
            <div className={styles["field-row"]}>
              <input
                className={styles["text-input"]}
                inputMode="numeric"
                placeholder="Pieces to add"
                value={restockAmount}
                onChange={(e) => setRestockAmount(e.target.value.replace(/[^0-9]/g, ""))}
              />
              <button
                type="button"
                className={styles["submit-button"]}
                disabled={!Number(restockAmount) || restockMutation.isPending}
                onClick={() => restockMutation.mutate(Number(restockAmount))}
              >
                {restockMutation.isPending ? "Adding..." : "Add Stock"}
              </button>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
