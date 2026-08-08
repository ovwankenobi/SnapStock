import { centsToPeso } from "../../lib/format";
import styles from "./sales.module.css";

export default function CheckoutSummary({ subtotalCents, onCompleteSale, disabled }) {
  return (
    <div className={styles["summary-panel"]}>
      <div className={styles["summary-label"]}>Subtotal</div>
      <div className={styles["summary-value"]}>{centsToPeso(subtotalCents)}</div>
      <button type="button" className={styles["summary-button"]} disabled={disabled} onClick={onCompleteSale}>
        Complete Sale
      </button>
    </div>
  );
}
