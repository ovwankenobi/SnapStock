import { useState } from "react";

import QuantityStepper from "../../components/QuantityStepper";
import SegmentedControl from "../../components/SegmentedControl";
import { centsToPeso, unitSuffix } from "../../lib/format";
import styles from "./inventory.module.css";

const PAYMENT_OPTIONS = [
  { value: "cash", label: "Cash" },
  { value: "gcash", label: "GCash" },
  { value: "maya", label: "Maya" },
];

export default function QuickSellSheet({ product, onConfirm, onClose, isSubmitting, error }) {
  const [quantity, setQuantity] = useState(1);
  const [paymentMethod, setPaymentMethod] = useState("cash");

  const unit = unitSuffix(product.unitType);
  const maxQuantity = Math.max(1, Math.floor(product.stockPieces / product.piecesPerUnit));
  const total = product.priceCents * quantity;

  return (
    <div className={styles["sheet-backdrop"]} onClick={onClose}>
      <div className={styles.sheet} onClick={(event) => event.stopPropagation()}>
        <div className={styles["sheet-title"]}>{product.name}</div>
        <div className={styles["sheet-sub"]}>
          {product.stockPieces} {unit} available
        </div>

        <QuantityStepper
          quantity={quantity}
          onIncrement={() => setQuantity((qty) => Math.min(qty + 1, maxQuantity))}
          onDecrement={() => setQuantity((qty) => Math.max(1, qty - 1))}
        />

        <SegmentedControl options={PAYMENT_OPTIONS} value={paymentMethod} onChange={setPaymentMethod} />

        <div className={styles["sheet-total"]}>Total: {centsToPeso(total)}</div>

        {error && <div className={styles["sheet-error"]}>{error}</div>}

        <button
          type="button"
          className={styles["submit-button"]}
          disabled={isSubmitting}
          onClick={() => onConfirm({ quantity, paymentMethod })}
        >
          {isSubmitting ? "Selling..." : "Confirm Sale"}
        </button>
      </div>
    </div>
  );
}
