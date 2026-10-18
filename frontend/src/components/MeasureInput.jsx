import { sanitizeQuantityInput } from "../lib/format";
import styles from "./primitives.module.css";

// Decimal amount entry for measure products; `value` is the raw text, parsed by the caller.
export default function MeasureInput({ value, onChange, unitLabel, ariaLabel = "Amount" }) {
  return (
    <div className={styles["measure-input"]}>
      <input
        inputMode="decimal"
        placeholder="0"
        aria-label={ariaLabel}
        value={value}
        onChange={(e) => onChange(sanitizeQuantityInput(e.target.value, "measure"))}
      />
      <span>{unitLabel}</span>
    </div>
  );
}
