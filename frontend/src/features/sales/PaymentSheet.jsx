import { useState } from "react";

import Sheet from "../../components/Sheet";
import { centsToPeso } from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import PaymentMethodPicker from "../payouts/PaymentMethodPicker";
import QrPayScreen, { qrAccountsFor } from "../payouts/QrPayScreen";
import styles from "./sales.module.css";

// Shown after "Complete Sale": the seller picks how the buyer paid, then confirms. A non-cash
// method with a QR first shows that QR full screen for the customer to scan.
export default function PaymentSheet({
  totalCents,
  paymentMethod,
  onPaymentMethodChange,
  onConfirm,
  onClose,
  isSubmitting,
  error,
}) {
  const { user, t } = useAuth();
  const [showQr, setShowQr] = useState(false);
  const qrAccounts = qrAccountsFor(user?.sellerProfile?.payoutAccounts, paymentMethod);

  if (showQr && qrAccounts.length > 0) {
    return (
      <QrPayScreen
        accounts={qrAccounts}
        totalCents={totalCents}
        onConfirm={onConfirm}
        onBack={() => setShowQr(false)}
        isSubmitting={isSubmitting}
        error={error}
      />
    );
  }

  return (
    <Sheet onClose={isSubmitting ? undefined : onClose} centered label={t("payouts.paymentTitle")}>
      <div className={styles["status-sheet"]}>
        <div className={styles["status-sheet-title"]}>{t("payouts.paymentTitle")}</div>
        <div className={styles["payment-sheet-total"]}>
          <span>{t("payouts.total")}</span>
          <strong>{centsToPeso(totalCents)}</strong>
        </div>

        <PaymentMethodPicker
          accounts={user?.sellerProfile?.payoutAccounts}
          value={paymentMethod}
          onChange={onPaymentMethodChange}
          hint={t("payouts.showToBuyerHint")}
        />

        {error && (
          <div className={styles["form-error"]} role="alert">
            {error}
          </div>
        )}

        <div className={styles["payment-sheet-actions"]}>
          <button type="button" className={styles["status-sheet-confirm"]} disabled={isSubmitting}
            onClick={qrAccounts.length > 0 ? () => setShowQr(true) : onConfirm}
          >
            {isSubmitting ? t("payouts.completing") : t("payouts.confirmPayment")}
          </button>
          <button type="button" className={styles["status-sheet-cancel"]} disabled={isSubmitting} onClick={onClose}>
            {t("payouts.back")}
          </button>
        </div>
      </div>
    </Sheet>
  );
}
