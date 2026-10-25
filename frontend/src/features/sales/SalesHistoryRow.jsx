import Badge from "../../components/Badge";
import { centsToPeso } from "../../lib/format";
import { paymentMethodLabel, SALE_STATUS_TAG } from "./salesFormat";
import styles from "./sales.module.css";

const TAG = {
  itemized: { tone: "info", label: "Account" },
  walk_in: { tone: "neutral", label: "Walk-in" },
};

export default function SalesHistoryRow({ sale, onClick, showTag = true }) {
  const tag = TAG[sale.saleType] || TAG.walk_in;
  const isItemized = sale.saleType === "itemized";
  const statusTag = SALE_STATUS_TAG[sale.status];
  // A pending order isn't reversed money, so its amount isn't struck through.
  const isReversed = statusTag && sale.status !== "pending_payment";

  return (
    <button
      type="button"
      className={`${styles["history-row"]} ${showTag && isItemized ? styles["history-row-account"] : ""}`}
      onClick={onClick}
    >
      <div className={styles["history-row-top"]}>
        <div className={styles["history-row-title-group"]}>
          {showTag && <Badge tone={tag.tone}>{tag.label}</Badge>}
          <span className={styles["history-row-title"]}>{sale.title}</span>
          {statusTag && <Badge tone={statusTag.tone}>{statusTag.label}</Badge>}
        </div>
        <span
          className={`${styles["history-row-amount"]} ${isReversed ? styles["history-row-amount-reversed"] : ""}`}
        >
          {centsToPeso(sale.amountCents)}
        </span>
      </div>
      <div className={styles["history-row-bottom"]}>
        <div className={styles["history-row-meta"]}>
          {sale.paymentMethod && <Badge tone="neutral">{paymentMethodLabel(sale.paymentMethod)}</Badge>}
          <span className={styles["history-row-items"]}>{sale.itemsSummary || "—"}</span>
        </div>
        <span className={styles["history-row-time"]}>{sale.timeLabel}</span>
      </div>
    </button>
  );
}
