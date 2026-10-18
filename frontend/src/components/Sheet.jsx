import { useEffect } from "react";

import styles from "./primitives.module.css";

// Bottom sheet on phones, centered dialog on tablet/desktop. Closes on backdrop tap and Escape.
export default function Sheet({ onClose, centered = false, label, children }) {
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape") onClose?.();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className={styles["sheet-backdrop"]} onClick={onClose}>
      <div
        className={`${styles.sheet} ${centered ? styles["sheet-centered"] : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        onClick={(event) => event.stopPropagation()}
      >
        <div className={styles["sheet-handle"]} aria-hidden="true" />
        {children}
      </div>
    </div>
  );
}
