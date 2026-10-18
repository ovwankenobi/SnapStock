import styles from "./primitives.module.css";

const DIGITS = ["1", "2", "3", "4", "5", "6", "7", "8", "9"];
const MAX_DIGITS = 9;

// Applies one keypad key ("0"-"9", ".", "back", "clear") to the typed text. `maxDecimals` 0 = whole numbers only.
export function applyNumPadKey(value, key, maxDecimals) {
  if (key === "clear") return "";
  if (key === "back") return value.slice(0, -1);
  if (key === ".") {
    if (!maxDecimals || value.includes(".")) return value;
    return (value || "0") + ".";
  }
  if (!/^[0-9]$/.test(key)) return value;
  const [whole, decimals] = value.split(".");
  if (decimals !== undefined) return decimals.length >= maxDecimals ? value : value + key;
  if (whole.replace(/^0+/, "").length >= MAX_DIGITS) return value;
  return whole === "0" ? key : value + key;
}

// Big on-screen keypad. Whole-number pads swap the "." key for Clear.
export default function NumPad({ onKey, allowDecimal = false, labels = {} }) {
  return (
    <div className={styles.numpad}>
      {DIGITS.map((digit) => (
        <button key={digit} type="button" className={styles["numpad-key"]} onClick={() => onKey(digit)}>
          {digit}
        </button>
      ))}
      {allowDecimal ? (
        <button type="button" className={styles["numpad-key"]} onClick={() => onKey(".")} aria-label={labels.decimal || "Decimal point"}>
          .
        </button>
      ) : (
        <button type="button" className={`${styles["numpad-key"]} ${styles["numpad-key-muted"]}`} onClick={() => onKey("clear")}>
          {labels.clear || "C"}
        </button>
      )}
      <button type="button" className={styles["numpad-key"]} onClick={() => onKey("0")}>
        0
      </button>
      <button
        type="button"
        className={`${styles["numpad-key"]} ${styles["numpad-key-muted"]}`}
        onClick={() => onKey("back")}
        aria-label={labels.backspace || "Backspace"}
      >
        ⌫
      </button>
    </div>
  );
}
