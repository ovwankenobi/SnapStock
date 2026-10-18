import styles from "./primitives.module.css";

// `onValueClick`, when given, makes the number itself tappable (e.g. to open a keypad).
export default function QuantityStepper({ quantity, onIncrement, onDecrement, onValueClick, valueLabel = "Enter quantity" }) {
  return (
    <div className={styles.stepper}>
      <button type="button" onClick={onDecrement} aria-label="Decrease quantity">
        −
      </button>
      {onValueClick ? (
        <button type="button" className={styles["stepper-value-button"]} onClick={onValueClick} aria-label={valueLabel}>
          {quantity}
        </button>
      ) : (
        <div className={styles["stepper-value"]}>{quantity}</div>
      )}
      <button type="button" onClick={onIncrement} aria-label="Increase quantity">
        +
      </button>
    </div>
  );
}
