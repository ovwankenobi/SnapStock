import styles from "./primitives.module.css";

export default function QuantityStepper({ quantity, onIncrement, onDecrement }) {
  return (
    <div className={styles.stepper}>
      <button type="button" onClick={onDecrement} aria-label="Decrease quantity">
        −
      </button>
      <div className={styles["stepper-value"]}>{quantity}</div>
      <button type="button" onClick={onIncrement} aria-label="Increase quantity">
        +
      </button>
    </div>
  );
}
