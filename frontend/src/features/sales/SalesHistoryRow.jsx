import Badge from "../../components/Badge";
import { centsToPeso } from "../../lib/format";
import styles from "./sales.module.css";

const TAG = {
  itemized: { tone: "info", label: "Account" },
  walk_in: { tone: "neutral", label: "Walk-in" },
};

export default function SalesHistoryRow({ sale, onClick }) {
  const tag = TAG[sale.saleType] || TAG.walk_in;
  const isItemized = sale.saleType === "itemized";

  return (
    <button
      type="button"
      className={`${styles["history-row"]} ${isItemized ? styles["history-row-account"] : ""}`}
      onClick={onClick}
    >
      <div className={styles["history-row-top"]}>
        <div className={styles["history-row-title-group"]}>
          <Badge tone={tag.tone}>{tag.label}</Badge>
          <span className={styles["history-row-title"]}>{sale.title}</span>
        </div>
        <span className={styles["history-row-amount"]}>{centsToPeso(sale.amountCents)}</span>
      </div>
      <div className={styles["history-row-bottom"]}>
        <span className={styles["history-row-items"]}>{sale.itemsSummary || "—"}</span>
        <span className={styles["history-row-time"]}>{sale.timeLabel}</span>
      </div>
    </button>
  );
}
