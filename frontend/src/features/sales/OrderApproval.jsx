import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { confirmPayment, getSale, rejectOrder } from "../../api/sales";
import EmptyState from "../../components/EmptyState";
import LoadingState from "../../components/LoadingState";
import { mediaUrl } from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import ReceiptCard from "./ReceiptCard";
import SaleStatusSheet from "./SaleStatusSheet";
import { saleToReceipt } from "./salesFormat";
import styles from "./sales.module.css";

// One online order under New Sale → Buyer Account: the buyer's items are fixed, so the seller only
// checks the proof of payment and approves or rejects. `onApproved` gets the completed sale.
export default function OrderApproval({ saleId, onApproved, onRejected }) {
  const queryClient = useQueryClient();
  const { user, t } = useAuth();
  const [rejecting, setRejecting] = useState(false);

  const { data: sale, isLoading, isError } = useQuery({
    queryKey: ["sale", saleId],
    queryFn: () => getSale(saleId),
  });

  function onSaleChanged(updated) {
    queryClient.setQueryData(["sale", saleId], updated);
    for (const key of ["sales", "products", "lowStockProducts", "pendingOrders", "messages"]) {
      queryClient.invalidateQueries({ queryKey: [key] });
    }
    queryClient.invalidateQueries({ predicate: (query) => String(query.queryKey[0]).startsWith("analytics") });
  }

  const confirmMutation = useMutation({
    mutationFn: () => confirmPayment(saleId),
    onSuccess: (updated) => {
      onSaleChanged(updated);
      onApproved(updated);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (reason) => rejectOrder(saleId, reason),
    onSuccess: (updated) => {
      onSaleChanged(updated);
      setRejecting(false);
      onRejected(updated);
    },
  });

  if (isLoading) return <LoadingState message={t("orders.loading")} />;
  if (isError) return <EmptyState message={t("orders.loadError")} />;

  const isPending = sale.status === "pending_payment";
  const needsProof = isPending && sale.paymentMethod !== "cash" && !sale.paymentProofUrl;

  return (
    <div className={styles["order-review"]}>
      {!isPending && (
        <p className={styles["order-review-hint"]}>
          {t(`saleStatus.${sale.status}Notice`)}
          {sale.statusReason ? ` — ${sale.statusReason}` : ""}
        </p>
      )}

      {isPending &&
        (sale.paymentMethod === "cash" ? (
          <p className={styles["order-review-hint"]}>{t("orders.sellerCashHint")}</p>
        ) : sale.paymentProofUrl ? (
          <a href={mediaUrl(sale.paymentProofUrl)} target="_blank" rel="noreferrer">
            <img className={styles["order-review-proof"]} src={mediaUrl(sale.paymentProofUrl)} alt={t("orders.proofTitle")} />
            <span className={styles["order-review-hint"]}>{t("orders.viewFull")}</span>
          </a>
        ) : (
          <p className={styles["order-review-hint"]}>{t("orders.noProof")}</p>
        ))}

      <ReceiptCard receipt={saleToReceipt(sale, { shopName: user?.sellerProfile?.businessName })} />

      {isPending && (
        <>
          {confirmMutation.isError && (
            <div className={styles["form-error"]}>
              {confirmMutation.error?.response?.data?.detail || t("orders.confirmError")}
            </div>
          )}
          <button
            type="button"
            className={styles["receipt-home-button"]}
            disabled={needsProof || confirmMutation.isPending}
            onClick={() => confirmMutation.mutate()}
          >
            {confirmMutation.isPending ? t("orders.confirming") : t("orders.approve")}
          </button>
          <button type="button" className={styles["order-review-reject"]} onClick={() => setRejecting(true)}>
            {t("saleStatus.reject.action")}
          </button>
        </>
      )}

      {rejecting && (
        <SaleStatusSheet
          action="reject"
          sale={sale}
          isSubmitting={rejectMutation.isPending}
          error={rejectMutation.error?.response?.data?.detail || (rejectMutation.isError ? t("saleStatus.error") : "")}
          onConfirm={(reason) => rejectMutation.mutate(reason)}
          onClose={() => {
            rejectMutation.reset();
            setRejecting(false);
          }}
        />
      )}
    </div>
  );
}
