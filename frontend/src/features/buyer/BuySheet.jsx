import { useState } from "react";

import QuantityStepper from "../../components/QuantityStepper";
import SegmentedControl from "../../components/SegmentedControl";
import { centsToPeso, unitSuffix } from "../../lib/format";
import styles from "./buyer.module.css";

const PAYMENT_OPTIONS = [
  { value: "cash", label: "Cash" },
  { value: "gcash", label: "GCash" },
  { value: "maya", label: "Maya" },
];

export default function BuySheet({ product, onConfirm, onClose, isSubmitting, error }) {
  const [quantity, setQuantity] = useState(1);
  const [paymentMethod, setPaymentMethod] = useState("cash");

  const total = product.priceCents * quantity;

  return (
    <div className={styles["sheet-backdrop"]} onClick={onClose}>
      <div className={styles.sheet} onClick={(event) => event.stopPropagation()}>
        <div className={styles["sheet-title"]}>{product.name}</div>
        <div className={styles["sheet-sub"]}>
          {centsToPeso(product.priceCents)}/{unitSuffix(product.unitType)}
        </div>

        <QuantityStepper
          quantity={quantity}
          onIncrement={() => setQuantity((qty) => qty + 1)}
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
          {isSubmitting ? "Placing order..." : "Buy Now"}
        </button>
      </div>
    </div>
  );
}
