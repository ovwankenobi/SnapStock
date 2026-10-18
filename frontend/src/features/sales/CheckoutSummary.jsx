import { useState } from "react";

import { centsToPeso, centsToPesoInput, pesoInputToCents } from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import AmountPadSheet from "./AmountPadSheet";
import styles from "./sales.module.css";

export default function CheckoutSummary({ subtotalCents, discountCents = 0, onDiscountChange, onCompleteSale, disabled }) {
  const { t } = useAuth();
  const [isEditingDiscount, setIsEditingDiscount] = useState(false);
  const discountTooBig = discountCents > subtotalCents;
  const totalCents = Math.max(0, subtotalCents - discountCents);

  return (
    <div className={styles["summary-panel"]}>
      {onDiscountChange && (
        <div className={styles["summary-discount"]}>
          <span>{t("checkout.discount")}</span>
          <button type="button" className={styles["summary-discount-button"]} onClick={() => setIsEditingDiscount(true)}>
            {discountCents ? `−${centsToPeso(discountCents)}` : t("checkout.addDiscount")}
          </button>
        </div>
      )}
      {discountTooBig && <div className={styles["form-error"]}>{t("checkout.discountTooBig")}</div>}
      <div className={styles["summary-amount"]}>
        <div className={styles["summary-label"]}>
          {discountCents > 0 ? t("checkout.total") : t("checkout.subtotal")}
          {discountCents > 0 && !discountTooBig && (
            <span className={styles["summary-was"]}> · {centsToPeso(subtotalCents)}</span>
          )}
        </div>
        <div className={styles["summary-value"]}>{centsToPeso(totalCents)}</div>
      </div>
      <button
        type="button"
        className={styles["summary-button"]}
        disabled={disabled || discountTooBig}
        onClick={onCompleteSale}
      >
        Complete Sale
      </button>
      {isEditingDiscount && (
        <AmountPadSheet
          title={t("checkout.discount")}
          subtitle={`${t("checkout.subtotal")} ${centsToPeso(subtotalCents)}`}
          initialValue={discountCents ? centsToPesoInput(discountCents) : ""}
          maxDecimals={2}
          prefix="−₱"
          canConfirm={(value) => (pesoInputToCents(value) || 0) <= subtotalCents}
          renderFooter={(value) => {
            const cents = pesoInputToCents(value) || 0;
            return (
              <>
                {cents > subtotalCents && <div className={styles["form-error"]}>{t("checkout.discountTooBig")}</div>}
                <div className={styles["dialog-total-row"]}>
                  <div className={styles["dialog-total-label"]}>{t("checkout.total")}</div>
                  <div className={styles["dialog-total-value"]}>{centsToPeso(Math.max(0, subtotalCents - cents))}</div>
                </div>
              </>
            );
          }}
          onConfirm={(value) => {
            onDiscountChange(pesoInputToCents(value) || 0);
            setIsEditingDiscount(false);
          }}
          onClose={() => setIsEditingDiscount(false)}
        />
      )}
    </div>
  );
}
