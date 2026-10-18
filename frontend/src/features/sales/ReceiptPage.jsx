import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { useNavigate, useParams } from "react-router-dom";

import { confirmPayment, getSale, refundSale, rejectOrder, voidSale } from "../../api/sales";
import AppLayout from "../../components/AppLayout";
import { useAuth } from "../auth/AuthContext";
import { mediaUrl } from "../../lib/format";
import { sellerNavItems } from "../../lib/nav";
import ReceiptCard from "./ReceiptCard";
import SaleStatusSheet from "./SaleStatusSheet";
import { saleToReceipt } from "./salesFormat";
import styles from "./sales.module.css";

const STATUS_ACTIONS = { void: voidSale, refund: refundSale, reject: rejectOrder };

export default function ReceiptPage() {
  const { saleId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, t } = useAuth();
  const [statusAction, setStatusAction] = useState(null);

  const { data: sale, isLoading, isError } = useQuery({
    queryKey: ["sale", saleId],
    queryFn: () => getSale(saleId),
  });

  function onSaleChanged(updated) {
    queryClient.setQueryData(["sale", saleId], updated);
    // Stock or totals changed, and a pending order may have left the to-confirm list.
    for (const key of ["sales", "products", "lowStockProducts", "pendingOrders"]) {
      queryClient.invalidateQueries({ queryKey: [key] });
    }
    queryClient.invalidateQueries({ predicate: (query) => String(query.queryKey[0]).startsWith("analytics") });
  }

  const statusMutation = useMutation({
    mutationFn: ({ action, reason }) => STATUS_ACTIONS[action](saleId, reason),
    onSuccess: (updated) => {
      onSaleChanged(updated);
      setStatusAction(null);
    },
  });

  const confirmMutation = useMutation({
    mutationFn: () => confirmPayment(saleId),
    onSuccess: onSaleChanged,
  });

  const isPendingOrder = sale?.status === "pending_payment";
  const needsProof = isPendingOrder && sale.paymentMethod !== "cash" && !sale.paymentProofUrl;

  const publicUrl = sale ? `${window.location.origin}/r/${sale.receiptCode}` : "";

  return (
    <AppLayout navItems={sellerNavItems()} title="Receipt" backTo={-1}>
      <div className={styles["receipt-screen"]}>
        {isLoading && <p className={styles.hint}>Loading receipt...</p>}
        {isError && <p className={styles.hint}>Could not load this receipt.</p>}
        {sale && (
          <>
            {sale.status === "completed" ? (
              <>
                <div className={styles["receipt-check"]}>✓</div>
                <div className={styles["receipt-thanks"]}>Thank you for your purchase!</div>
              </>
            ) : (
              <div className={styles["receipt-thanks"]}>
                {t(`saleStatus.${sale.status}Notice`)}
                {sale.statusReason ? ` — ${sale.statusReason}` : ""}
              </div>
            )}
            <div className={styles["receipt-subtitle"]}>{sale.receiptCode}</div>

            {isPendingOrder && (
              <div className={`${styles["order-review"]} no-print`}>
                {sale.paymentMethod === "cash" ? (
                  <p className={styles["order-review-hint"]}>{t("orders.sellerCashHint")}</p>
                ) : sale.paymentProofUrl ? (
                  <a href={mediaUrl(sale.paymentProofUrl)} target="_blank" rel="noreferrer">
                    <img
                      className={styles["order-review-proof"]}
                      src={mediaUrl(sale.paymentProofUrl)}
                      alt={t("orders.proofTitle")}
                    />
                    <span className={styles["order-review-hint"]}>{t("orders.viewFull")}</span>
                  </a>
                ) : (
                  <p className={styles["order-review-hint"]}>{t("orders.noProof")}</p>
                )}
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
                  {confirmMutation.isPending ? t("orders.confirming") : t("orders.confirmPayment")}
                </button>
                <button type="button" className={styles["order-review-reject"]} onClick={() => setStatusAction("reject")}>
                  {t("saleStatus.reject.action")}
                </button>
              </div>
            )}

            <div className={`${styles["qr-wrap"]} no-print`}>
              <QRCodeSVG value={publicUrl} size={144} />
            </div>

            <ReceiptCard
              receipt={saleToReceipt(sale, { shopName: user?.sellerProfile?.businessName, servedBy: user?.fullName })}
            />

            <button
              type="button"
              className={`${styles["receipt-home-button"]} no-print`}
              onClick={() => navigate("/sales")}
            >
              New Sale
            </button>
            {sale.status === "completed" && (
              <div className={`${styles["receipt-status-actions"]} no-print`}>
                <button type="button" onClick={() => setStatusAction("refund")}>
                  {t("saleStatus.refund.action")}
                </button>
                <button type="button" onClick={() => setStatusAction("void")}>
                  {t("saleStatus.void.action")}
                </button>
              </div>
            )}
          </>
        )}
      </div>
      {statusAction && sale && (
        <SaleStatusSheet
          action={statusAction}
          sale={sale}
          isSubmitting={statusMutation.isPending}
          error={statusMutation.error?.response?.data?.detail || (statusMutation.isError ? t("saleStatus.error") : "")}
          onConfirm={(reason) => statusMutation.mutate({ action: statusAction, reason })}
          onClose={() => {
            statusMutation.reset();
            setStatusAction(null);
          }}
        />
      )}
    </AppLayout>
  );
}
