import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { cancelMyOrder, getMyOrder, uploadPaymentProof } from "../../api/catalog";
import AppLayout from "../../components/AppLayout";
import EmptyState from "../../components/EmptyState";
import LoadingState from "../../components/LoadingState";
import { mediaUrl } from "../../lib/format";
import { buyerNavItems } from "../../lib/nav";
import { useAuth } from "../auth/AuthContext";
import PayoutAccountCard from "../payouts/PayoutAccountCard";
import payoutStyles from "../payouts/payouts.module.css";
import ReceiptCard from "../sales/ReceiptCard";
import { saleToReceipt } from "../sales/salesFormat";
import styles from "./buyer.module.css";

// Where a buyer lands after ordering: pay the seller, upload proof, and watch for the seller's confirmation.
export default function OrderPage() {
  const { saleId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { t } = useAuth();
  const [confirmingCancel, setConfirmingCancel] = useState(false);

  const { data: order, isLoading, isError } = useQuery({
    queryKey: ["myOrder", saleId],
    queryFn: () => getMyOrder(saleId),
    // Poll while pending so the seller's confirmation shows up without a refresh.
    refetchInterval: (query) => (query.state.data?.status === "pending_payment" ? 10000 : false),
  });

  function onOrderChanged(updated) {
    queryClient.setQueryData(["myOrder", saleId], updated);
    queryClient.invalidateQueries({ queryKey: ["myReceipts"] });
  }

  const proofMutation = useMutation({
    mutationFn: (file) => uploadPaymentProof(saleId, file),
    onSuccess: onOrderChanged,
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelMyOrder(saleId),
    onSuccess: (updated) => {
      onOrderChanged(updated);
      setConfirmingCancel(false);
    },
  });

  const isPending = order?.status === "pending_payment";
  const isCash = order?.paymentMethod === "cash";
  const mutationError = proofMutation.isError
    ? proofMutation.error?.response?.data?.detail || t("orders.uploadError")
    : cancelMutation.isError
      ? cancelMutation.error?.response?.data?.detail || t("orders.cancelError")
      : "";

  function heading() {
    if (order.status === "completed") return t("orders.completedTitle");
    if (order.status === "cancelled") return t("orders.cancelledTitle");
    if (isPending) return t("orders.awaitingTitle");
    return t(`saleStatus.${order.status}Notice`);
  }

  return (
    <AppLayout navItems={buyerNavItems()} title={t("orders.orderTitle")} backTo="/buyer/receipts">
      <div className={styles["order-page"]}>
        {isLoading && <LoadingState message={t("orders.loading")} />}
        {isError && <EmptyState message={t("orders.loadError")} />}

        {order && (
          <>
            <div className={styles["order-heading"]}>{heading()}</div>
            {order.status === "cancelled" && order.statusReason && (
              <p className={styles["order-hint"]}>{order.statusReason}</p>
            )}

            {isPending && isCash && <p className={styles["order-hint"]}>{t("orders.buyerCashHint")}</p>}

            {isPending && !isCash && (
              <>
                {order.payoutAccounts.length > 0 ? (
                  <section className={payoutStyles.section}>
                    <div className={payoutStyles["field-label"]}>{t("orders.payTo")}</div>
                    <div className={styles["seller-pay-via-grid"]}>
                      {order.payoutAccounts.map((account) => (
                        <PayoutAccountCard key={account.id} account={account} stacked />
                      ))}
                    </div>
                  </section>
                ) : (
                  <p className={styles["order-hint"]}>{t("orders.noPayoutAccounts")}</p>
                )}

                {order.paymentProofUrl && (
                  <>
                    <img
                      className={styles["order-proof"]}
                      src={mediaUrl(order.paymentProofUrl)}
                      alt={t("orders.proofTitle")}
                    />
                    <p className={styles["order-hint"]}>{t("orders.proofSent")}</p>
                  </>
                )}

                <label className={styles["order-upload"]}>
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    disabled={proofMutation.isPending}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      e.target.value = "";
                      if (file) proofMutation.mutate(file);
                    }}
                  />
                  {proofMutation.isPending
                    ? t("orders.uploading")
                    : order.paymentProofUrl
                      ? t("orders.replaceProof")
                      : t("orders.uploadProof")}
                </label>
              </>
            )}

            {mutationError && <div className={styles["sheet-error"]}>{mutationError}</div>}

            <ReceiptCard receipt={saleToReceipt(order, { shopName: order.sellerName })} />

            {order.status === "completed" && (
              <button
                type="button"
                className={styles["sheet-submit"]}
                onClick={() => navigate(`/r/${order.receiptCode}`)}
              >
                {t("orders.viewReceipt")}
              </button>
            )}

            {isPending && (
              <button
                type="button"
                className={styles["order-cancel"]}
                disabled={cancelMutation.isPending}
                onClick={() => (confirmingCancel ? cancelMutation.mutate() : setConfirmingCancel(true))}
              >
                {confirmingCancel ? t("orders.cancelConfirm") : t("orders.cancelOrder")}
              </button>
            )}
          </>
        )}
      </div>
    </AppLayout>
  );
}
