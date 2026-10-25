import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { centsToPeso, mediaUrl } from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import { payoutAccountTitle } from "./payoutFormat";
import styles from "./payouts.module.css";

// The seller's payout accounts for `method` that have a QR image, default account first.
export function qrAccountsFor(accounts = [], method) {
  if (method === "cash") return [];
  return accounts
    .filter((account) => account.method === method && account.qrUrl)
    .sort((a, b) => Number(b.isDefault) - Number(a.isDefault));
}

// Full-screen QR shown to a walk-in customer before the seller completes a non-cash sale.
// Portaled to <body> so it escapes the sheet's scroll container and covers the whole screen.
// With `onProofChange`, the seller can also photograph the customer's payment confirmation (optional).
export default function QrPayScreen({
  accounts,
  totalCents,
  onConfirm,
  onBack,
  isSubmitting,
  error,
  proofFile,
  onProofChange,
}) {
  const { t } = useAuth();
  const [index, setIndex] = useState(0);
  const account = accounts[Math.min(index, accounts.length - 1)];
  const title = payoutAccountTitle(t, account);
  const [proofPreview, setProofPreview] = useState(null);

  useEffect(() => {
    if (!proofFile) {
      setProofPreview(null);
      return undefined;
    }
    const url = URL.createObjectURL(proofFile);
    setProofPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [proofFile]);

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape" && !isSubmitting) onBack();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onBack, isSubmitting]);

  return createPortal(
    <div className={styles["qr-screen"]} role="dialog" aria-modal="true" aria-label={`${title} QR`}>
      <div className={styles["qr-screen-total"]}>
        <span>{t("payouts.total")}</span>
        <strong>{centsToPeso(totalCents)}</strong>
      </div>

      <img className={styles["qr-screen-image"]} src={mediaUrl(account.qrUrl)} alt={`${title} QR`} />

      <div className={styles["qr-screen-details"]}>
        <div className={styles["card-title"]}>{title}</div>
        <div className={styles["card-name"]}>{account.accountName}</div>
        <div className={styles["card-number"]}>{account.accountNumber}</div>
      </div>

      {accounts.length > 1 && (
        <div className={styles["qr-screen-switch"]}>
          {accounts.map((other, otherIndex) => (
            <button
              key={other.id}
              type="button"
              aria-pressed={other.id === account.id}
              onClick={() => setIndex(otherIndex)}
            >
              {other.accountName || payoutAccountTitle(t, other)}
            </button>
          ))}
        </div>
      )}

      {onProofChange && (
        <>
          <div className={styles["qr-screen-proof"]}>
            {proofPreview && (
              <div className={styles["qr-screen-proof-thumb"]}>
                <img src={proofPreview} alt={t("payouts.paymentPhotoTitle")} />
                <button
                  type="button"
                  aria-label={t("payouts.removeReceiptPhoto")}
                  disabled={isSubmitting}
                  onClick={() => onProofChange(null)}
                >
                  ×
                </button>
              </div>
            )}
            <label className={styles["qr-screen-photo"]} aria-disabled={isSubmitting}>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                capture="environment"
                disabled={isSubmitting}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  e.target.value = "";
                  if (file) onProofChange(file);
                }}
              />
              {proofFile ? t("payouts.retakeReceiptPhoto") : t("payouts.takeReceiptPhoto")}
            </label>
          </div>
          {!proofFile && <p className={styles["qr-screen-proof-hint"]}>{t("payouts.receiptPhotoHint")}</p>}
        </>
      )}

      {error && (
        <div className={styles.error} role="alert">
          {error}
        </div>
      )}

      <div className={styles["qr-screen-actions"]}>
        <button type="button" className={styles.primary} disabled={isSubmitting} onClick={onConfirm}>
          {isSubmitting ? t("payouts.completing") : t("payouts.paidComplete")}
        </button>
        <button type="button" className={styles.secondary} disabled={isSubmitting} onClick={onBack}>
          {t("payouts.back")}
        </button>
      </div>
    </div>,
    document.body,
  );
}
