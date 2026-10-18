import { useState } from "react";

import Sheet from "../../components/Sheet";
import { centsToPeso } from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import styles from "./sales.module.css";

// Confirms a void, refund or order rejection. All put the stock back; a void or rejection also keeps it out of every report.
export default function SaleStatusSheet({ action, sale, onConfirm, onClose, isSubmitting, error }) {
  const { t } = useAuth();
  const [reason, setReason] = useState("");

  return (
    <Sheet onClose={onClose} centered label={t(`saleStatus.${action}.title`)}>
      <div className={styles["status-sheet"]}>
        <div className={styles["status-sheet-title"]}>{t(`saleStatus.${action}.title`)}</div>
        <p className={styles["status-sheet-body"]}>
          {t(`saleStatus.${action}.body`, { amount: centsToPeso(sale.totalCents) })}
        </p>
        <label className={styles["status-sheet-field"]}>
          <span>{t("saleStatus.reason")}</span>
          <input
            value={reason}
            maxLength={500}
            placeholder={t(`saleStatus.${action}.reasonPlaceholder`)}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
        {error && <div className={styles["form-error"]}>{error}</div>}
        <button
          type="button"
          className={`${styles["status-sheet-confirm"]} ${action === "refund" ? "" : styles["status-sheet-danger"]}`}
          disabled={isSubmitting}
          onClick={() => onConfirm(reason.trim())}
        >
          {isSubmitting ? t("saleStatus.saving") : t(`saleStatus.${action}.confirm`)}
        </button>
        <button type="button" className={styles["status-sheet-cancel"]} onClick={onClose}>
          {t("saleStatus.cancel")}
        </button>
      </div>
    </Sheet>
  );
}
