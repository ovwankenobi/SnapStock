import { useEffect, useRef, useState } from "react";

import NumPad, { applyNumPadKey } from "../../components/NumPad";
import Sheet from "../../components/Sheet";
import { useAuth } from "../auth/AuthContext";
import styles from "./sales.module.css";

const KEYBOARD_KEYS = { Backspace: "back", Delete: "clear", ",": "." };

// Bottom sheet with a big keypad for entering one number (quantity, price, discount).
// The first key press replaces `initialValue`, like a calculator; `onConfirm` gets the typed text.
export default function AmountPadSheet({
  title,
  subtitle,
  initialValue = "",
  maxDecimals = 0,
  prefix,
  suffix,
  presets = [],
  renderFooter,
  confirmLabel,
  canConfirm = (value) => value !== "",
  onConfirm,
  onClose,
}) {
  const { t } = useAuth();
  const [value, setValue] = useState(initialValue);
  const [fresh, setFresh] = useState(initialValue !== "");

  function press(key) {
    setFresh(false);
    setValue((current) => applyNumPadKey(fresh && key !== "back" ? "" : current, key, maxDecimals));
  }

  // The physical-keyboard listener is attached once, so it reads the current render's values from here.
  const latest = useRef({});
  latest.current = { value, canConfirm, onConfirm, press };

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      const { value: current, canConfirm: allowed, onConfirm: confirm } = latest.current;
      if (event.key === "Enter") {
        event.preventDefault();
        if (allowed(current)) confirm(current);
        return;
      }
      const key = KEYBOARD_KEYS[event.key] || event.key;
      if (/^[0-9.]$/.test(key) || key === "back" || key === "clear") {
        event.preventDefault();
        latest.current.press(key);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const enabled = canConfirm(value);

  return (
    <Sheet onClose={onClose} label={title}>
      <div className={styles["dialog-header"]}>
        <div>
          <div className={styles["dialog-title"]}>{title}</div>
          {subtitle && <div className={styles["dialog-subtitle"]}>{subtitle}</div>}
        </div>
        <button type="button" className={styles["dialog-close"]} onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>

      <div className={styles["pad-display"]} aria-live="polite">
        {prefix && <span className={styles["pad-affix"]}>{prefix}</span>}
        <span className={`${styles["pad-value"]} ${fresh ? styles["pad-value-fresh"] : ""} ${value ? "" : styles["pad-value-empty"]}`}>
          {value || "0"}
        </span>
        {suffix && <span className={styles["pad-affix"]}>{suffix}</span>}
      </div>

      {presets.length > 0 && (
        <div className={styles["dialog-presets"]}>
          {presets.map((preset) => (
            <button
              key={preset.value}
              type="button"
              className={styles["dialog-preset"]}
              onClick={() => {
                setFresh(false);
                setValue(preset.value);
              }}
            >
              {preset.label}
            </button>
          ))}
        </div>
      )}

      <NumPad
        onKey={press}
        allowDecimal={maxDecimals > 0}
        labels={{ clear: t("numpad.clear"), backspace: t("numpad.backspace"), decimal: t("numpad.decimal") }}
      />

      {renderFooter?.(value)}

      <button type="button" className={styles["dialog-confirm"]} onClick={() => onConfirm(value)} disabled={!enabled}>
        {typeof confirmLabel === "function" ? confirmLabel(value) : confirmLabel || t("numpad.done")}
      </button>
    </Sheet>
  );
}
