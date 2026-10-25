import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { confirmPayment, getSale, refundSale, rejectOrder, uploadSaleProof, voidSale } from "../../api/sales";
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
  const location = useLocation();
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

  // Seller's photo of a walk-in customer's digital payment, taken on the QR screen or added here.
  const proofMutation = useMutation({
    mutationFn: (file) => uploadSaleProof(saleId, file),
    onSuccess: (updated) => {
      queryClient.setQueryData(["sale", saleId], updated);
      queryClient.invalidateQueries({ queryKey: ["sales"] });
    },
  });

  const isPendingOrder = sale?.status === "pending_payment";
  const needsProof = isPendingOrder && sale.paymentMethod !== "cash" && !sale.paymentProofUrl;
  const showPaymentPhoto =
    sale?.saleType === "walk_in" &&
    sale.paymentMethod !== "cash" &&
    (sale.status === "completed" || Boolean(sale.paymentProofUrl));

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

            {showPaymentPhoto && (
              <div className={`${styles["order-review"]} no-print`}>
                <div className={styles["order-review-hint"]}>{t("payouts.paymentPhotoTitle")}</div>
                {location.state?.proofFailed && !sale.paymentProofUrl && (
                  <div className={styles["form-error"]}>{t("payouts.proofUploadFailed")}</div>
                )}
                {sale.paymentProofUrl && (
                  <a href={mediaUrl(sale.paymentProofUrl)} target="_blank" rel="noreferrer">
                    <img
                      className={styles["order-review-proof"]}
                      src={mediaUrl(sale.paymentProofUrl)}
                      alt={t("payouts.paymentPhotoTitle")}
                    />
                    <span className={styles["order-review-hint"]}>{t("orders.viewFull")}</span>
                  </a>
                )}
                {proofMutation.isError && (
                  <div className={styles["form-error"]}>
                    {proofMutation.error?.response?.data?.detail || t("payouts.photoUploadError")}
                  </div>
                )}
                {sale.status === "completed" && (
                  <label className={styles["receipt-photo-button"]}>
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      capture="environment"
                      disabled={proofMutation.isPending}
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        e.target.value = "";
                        if (file) proofMutation.mutate(file);
                      }}
                    />
                    {proofMutation.isPending
                      ? t("payouts.uploadingPhoto")
                      : sale.paymentProofUrl
                        ? t("payouts.retakeReceiptPhoto")
                        : t("payouts.addPaymentPhoto")}
                  </label>
                )}
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
