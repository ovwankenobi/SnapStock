import { centsToPeso } from "../../lib/format";
import styles from "./sales.module.css";

export default function WeighDialog({ product, grams, onGramsChange, presets, onPresetSelect, onConfirm, onClose }) {
  const totalCents = product.priceCents * (Number(grams) || 0);

  return (
    <div className={styles["dialog-backdrop"]}>
      <div className={styles.dialog}>
        <div className={styles["dialog-header"]}>
          <div>
            <div className={styles["dialog-title"]}>{product.name}</div>
            <div className={styles["dialog-subtitle"]}>{centsToPeso(product.priceCents)}/g</div>
          </div>
          <button type="button" className={styles["dialog-close"]} onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className={styles["dialog-grams-row"]}>
          <input
            className={styles["dialog-grams-input"]}
            inputMode="numeric"
            placeholder="0"
            value={grams}
            onChange={(e) => onGramsChange(e.target.value.replace(/[^0-9]/g, ""))}
          />
          <div className={styles["dialog-unit"]}>g</div>
        </div>
        <div className={styles["dialog-presets"]}>
          {presets.map((preset) => (
            <button key={preset} type="button" className={styles["dialog-preset"]} onClick={() => onPresetSelect(preset)}>
              {preset >= 1000 ? `${preset / 1000}kg` : `${preset}g`}
            </button>
          ))}
        </div>
        <div className={styles["dialog-total-row"]}>
          <div className={styles["dialog-total-label"]}>Subtotal</div>
          <div className={styles["dialog-total-value"]}>{centsToPeso(totalCents)}</div>
        </div>
        <button type="button" className={styles["dialog-confirm"]} onClick={onConfirm} disabled={!(Number(grams) > 0)}>
          Add to Cart
        </button>
      </div>
    </div>
  );
}
