import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { buyProduct, getCatalogProduct } from "../../api/catalog";
import { createConversation } from "../../api/messages";
import AppLayout from "../../components/AppLayout";
import Badge from "../../components/Badge";
import EmptyState from "../../components/EmptyState";
import ActionBar from "../../components/ActionBar";
import { centsToPeso, colorForKey, isBundle, mediaUrl, perPieceCents, unitSuffix } from "../../lib/format";
import { buyerNavItems } from "../../lib/nav";
import { useAuth } from "../auth/AuthContext";
import styles from "./buyer.module.css";
import { stockBadge } from "./buyerFormat";
import BuySheet from "./BuySheet";

export default function ProductDetailPage() {
  const { productId } = useParams();
  const navigate = useNavigate();
  const { t } = useAuth();
  const [showBuySheet, setShowBuySheet] = useState(false);
  const [buyError, setBuyError] = useState("");

  const { data: product, isLoading, isError } = useQuery({
    queryKey: ["catalogProduct", productId],
    queryFn: () => getCatalogProduct(productId),
  });

  const badge = product ? stockBadge(product.stockStatus) : null;

  const buyMutation = useMutation({
    mutationFn: (payload) => buyProduct(productId, payload),
    onSuccess: (sale) => {
      navigate(`/buyer/orders/${sale.id}`);
    },
    onError: (err) => {
      setBuyError(err.response?.data?.detail || "Could not place the order.");
    },
  });

  const messageSellerMutation = useMutation({
    mutationFn: () => createConversation({ otherUserId: product.sellerId, productId: product.id }),
    onSuccess: (conversation) => {
      navigate(`/messages/${conversation.id}`);
    },
  });

  return (
    <AppLayout
      navItems={buyerNavItems()}
      title="Product"
      backTo={-1}
      hideBottomNav
    >
      {isLoading && <p className={styles.hint}>Loading product...</p>}
      {isError && <EmptyState message="Could not load this product." />}

      {product && (
        <div className={styles.detail}>
          {product.photoUrl ? (
            <img className={styles["detail-photo"]} src={mediaUrl(product.photoUrl)} alt={product.name} />
          ) : (
            <div
              className={styles["detail-photo-fallback"]}
              style={{ background: colorForKey(product.category || product.name) }}
            >
              {(product.category || product.name || "?").charAt(0).toUpperCase()}
            </div>
          )}

          <div className={styles["detail-heading"]}>
            <div>
              <div className={styles["detail-name"]}>{product.name}</div>
              <div className={styles["detail-price"]}>
                {centsToPeso(product.priceCents)}/{unitSuffix(product.unitType, product.unitLabel)}
              </div>
              {isBundle(product.unitType) && (
                <div className={styles["detail-note"]}>
                  {t("checkout.alsoPerPiece", {
                    price: centsToPeso(perPieceCents(product.priceCents, product.piecesPerUnit)),
                  })}
                </div>
              )}
            </div>
            <Badge tone={badge.tone}>{badge.label}</Badge>
          </div>

          {product.description && <div className={styles["detail-description"]}>{product.description}</div>}

          <button
            type="button"
            className={styles["seller-card"]}
            onClick={() => navigate(`/buyer/sellers/${product.sellerId}`)}
          >
            <div>
              <div className={styles["seller-card-label"]}>Sold by</div>
              <div className={styles["seller-card-name"]}>{product.sellerName}</div>
            </div>
          </button>

          <ActionBar>
            <button
              type="button"
              className={styles["detail-action-secondary"]}
              disabled={messageSellerMutation.isPending}
              onClick={() => messageSellerMutation.mutate()}
            >
              Message Seller
            </button>
            <button
              type="button"
              className={styles["detail-action-primary"]}
              disabled={product.stockStatus === "out"}
              onClick={() => {
                setBuyError("");
                setShowBuySheet(true);
              }}
            >
              {product.stockStatus === "out" ? "Out of Stock" : "Buy"}
            </button>
          </ActionBar>
        </div>
      )}

      {showBuySheet && product && (
        <BuySheet
          product={product}
          isSubmitting={buyMutation.isPending}
          error={buyError}
          onClose={() => setShowBuySheet(false)}
          onConfirm={(payload) => buyMutation.mutate(payload)}
        />
      )}
    </AppLayout>
  );
}
