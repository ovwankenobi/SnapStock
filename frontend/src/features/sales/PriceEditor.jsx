import { useState } from "react";

import { centsToPeso, centsToPesoInput, pesoInputToCents } from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import AmountPadSheet from "./AmountPadSheet";
import styles from "./sales.module.css";

// The unit price for one sale line. Starts at the product's list price; tapping it opens a keypad so the
// seller can enter the agreed price for this transaction only (the product's own price never changes).
export default function PriceEditor({ productName, listPriceCents, priceCents, costCents, unitLabel, onChange }) {
  const { t } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const isEdited = priceCents !== listPriceCents;
  const belowCost = costCents != null && priceCents < costCents;

  function commit(value) {
    const cents = pesoInputToCents(value);
    setIsEditing(false);
    if (cents == null) return;
    onChange(cents === listPriceCents ? null : cents);
  }

  return (
    <div className={styles["price-editor-display"]}>
      <button
        type="button"
        className={`${styles["price-editor-button"]} ${isEdited ? styles["price-editor-edited"] : ""}`}
        onClick={() => setIsEditing(true)}
        aria-label={t("checkout.editPrice")}
      >
        {centsToPeso(priceCents)} / {unitLabel} ✎
      </button>
      {isEdited && (
        <span className={styles["cart-item-price"]}>
          {t("checkout.wasPrice", { price: centsToPeso(listPriceCents) })}{" "}
          <button type="button" className={styles["price-editor-reset"]} onClick={() => onChange(null)}>
            {t("checkout.resetPrice")}
          </button>
        </span>
      )}
      {belowCost && <span className={styles["price-editor-warning"]}>{t("checkout.belowCost")}</span>}
      {isEditing && (
        <AmountPadSheet
          title={t("checkout.unitPrice")}
          subtitle={`${productName} · ${t("checkout.listPrice", { price: centsToPeso(listPriceCents) })}`}
          initialValue={centsToPesoInput(priceCents)}
          maxDecimals={2}
          prefix="₱"
          suffix={`/ ${unitLabel}`}
          renderFooter={(value) => {
            const cents = pesoInputToCents(value);
            return costCents != null && cents != null && cents < costCents ? (
              <div className={styles["price-editor-warning"]}>{t("checkout.belowCost")}</div>
            ) : null;
          }}
          onConfirm={commit}
          onClose={() => setIsEditing(false)}
        />
      )}
    </div>
  );
}
