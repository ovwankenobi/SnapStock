import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import {
  createProduct,
  deleteProduct,
  getProduct,
  restockProduct,
  updateProduct,
  uploadProductPhoto,
} from "../../api/products";
import AppLayout from "../../components/AppLayout";
import EmptyState from "../../components/EmptyState";
import LoadingState from "../../components/LoadingState";
import {
  formatQuantity,
  isMeasured,
  parseQuantityInput,
  sanitizeQuantityInput,
  unitSuffix,
  centsToPesoInput,
  pesoInputToCents,
} from "../../lib/format";
import { sellerNavItems } from "../../lib/nav";
import styles from "./inventory.module.css";
import ProductForm from "./ProductForm";

const EMPTY_DRAFT = {
  name: "",
  priceInput: "",
  costInput: "",
  unitType: "piece",
  unitLabel: "kg",
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
    costInput: centsToPesoInput(product.costCents),
    unitType: product.unitType,
    unitLabel: product.unitLabel || "kg",
    piecesPerUnitInput: String(product.piecesPerUnit),
    stockInput: formatQuantity(product.unitType, product.stockPieces),
    lowStockThresholdInput: formatQuantity(product.unitType, product.lowStockThreshold),
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
      setDraft((current) => ({ ...current, stockInput: formatQuantity(updated.unitType, updated.stockPieces) }));
      setRestockAmount("");
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["lowStockProducts"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteProduct(productId),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["product", productId] });
      invalidateAndReturn();
    },
    onError: () => setError("Could not delete product. Try again."),
  });

  function handleDelete() {
    if (!window.confirm(`Delete "${product?.name ?? "this product"}"? It will be removed from your inventory. Past sales and receipts are kept.`)) {
      return;
    }
    setError("");
    deleteMutation.mutate();
  }

  const isSubmitting = createMutation.isPending || updateMutation.isPending;
  // Restock applies to the saved product, so use its unit rather than unsaved draft edits.
  const restockUnitType = product?.unitType ?? draft.unitType;
  const restockQuantity = parseQuantityInput(restockAmount, restockUnitType);

  function buildPayload() {
    const unitType = draft.unitType;
    return {
      name: draft.name.trim(),
      description: draft.description.trim() || null,
      priceCents: Number(draft.priceInput) * 100,
      // Blank = not recorded yet; a cost can be corrected later but not cleared.
      costCents: pesoInputToCents(draft.costInput) ?? undefined,
      unitType,
      unitLabel: isMeasured(unitType) ? draft.unitLabel.trim() : null,
      piecesPerUnit: unitType === "bundle" ? Number(draft.piecesPerUnitInput) || 1 : 1,
      lowStockThreshold: parseQuantityInput(draft.lowStockThresholdInput, unitType),
      category: draft.category.trim() || null,
    };
  }

  function handleSubmit() {
    setError("");
    if (!draft.name.trim() || !Number(draft.priceInput)) {
      setError("Name and price are required.");
      return;
    }
    if (isMeasured(draft.unitType) && !draft.unitLabel.trim()) {
      setError("Choose or type a unit of measure.");
      return;
    }

    if (isEditing) {
      updateMutation.mutate(buildPayload());
    } else {
      createMutation.mutate({ ...buildPayload(), stockPieces: parseQuantityInput(draft.stockInput, draft.unitType) });
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
      <AppLayout navItems={sellerNavItems()} title="Edit Product" backTo="/inventory" hideBottomNav>
        <div className={styles.page}>
          <LoadingState message="Loading product…" />
        </div>
      </AppLayout>
    );
  }

  if (isEditing && isProductError) {
    return (
      <AppLayout navItems={sellerNavItems()} title="Edit Product" backTo="/inventory" hideBottomNav>
        <div className={styles.page}>
          <EmptyState message="Could not load this product." />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout
      navItems={sellerNavItems()}
      title={isEditing ? "Edit Product" : "Add Product"}
      backTo="/inventory"
      hideBottomNav
    >
      <div className={styles.page}>
        <ProductForm
          value={{ ...draft, hideStock: isEditing }}
          onFieldChange={(field, fieldValue) => setDraft((current) => ({ ...current, [field]: fieldValue }))}
          onSubmit={handleSubmit}
          onPhotoSelect={handlePhotoSelect}
          submitLabel={isEditing ? "Save Changes" : "Create Product"}
          isSubmitting={isSubmitting}
        />

        {error && <div className={styles["sheet-error"]}>{error}</div>}

        {isEditing && (
          <div className={styles["form-panel"]}>
            <div className={styles["field-label"]}>
              Restock · Current stock: {draft.stockInput}{" "}
              {isMeasured(restockUnitType) ? unitSuffix(restockUnitType, product?.unitLabel) : "pieces"}
            </div>
            <div className={styles["inline-row"]}>
              <input
                className={styles["text-input"]}
                inputMode={isMeasured(restockUnitType) ? "decimal" : "numeric"}
                placeholder={
                  isMeasured(restockUnitType)
                    ? `${unitSuffix(restockUnitType, product?.unitLabel)} to add`
                    : "Pieces to add"
                }
                value={restockAmount}
                onChange={(e) => setRestockAmount(sanitizeQuantityInput(e.target.value, restockUnitType))}
              />
              <button
                type="button"
                className={styles["submit-button"]}
                disabled={!restockQuantity || restockMutation.isPending}
                onClick={() => restockMutation.mutate(restockQuantity)}
              >
                {restockMutation.isPending ? "Adding..." : "Add Stock"}
              </button>
            </div>
          </div>
        )}

        {isEditing && (
          <div className={styles["form-panel"]}>
            <div className={styles["field-label"]}>Delete product</div>
            <button
              type="button"
              className={styles["delete-button"]}
              disabled={deleteMutation.isPending}
              onClick={handleDelete}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete Product"}
            </button>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
