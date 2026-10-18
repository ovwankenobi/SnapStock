import { useState } from "react";

import Badge from "../../components/Badge";
import Icon from "../../components/Icon";
import styles from "./sales.module.css";

function daysLabel(days) {
  if (days == null) return "Not enough sales history yet";
  const rounded = Math.round(days);
  if (rounded < 1) return "Could run out today";
  return `~${rounded} day${rounded === 1 ? "" : "s"} of stock left`;
}

// Collapsed to a one-line summary on phones so the sales list stays near the top; always open on desktop (CSS).
export default function DemandForecastList({ forecasts }) {
  const [isOpen, setIsOpen] = useState(false);
  const items = [...(forecasts || [])].sort((a, b) => {
    const aDays = a.daysOfStockRemaining ?? Infinity;
    const bDays = b.daysOfStockRemaining ?? Infinity;
    return aDays - bDays;
  });
  const atRiskCount = items.filter((item) => item.atRisk).length;

  return (
    <div className={`${styles["forecast-card"]} ${isOpen ? styles["forecast-card-open"] : ""}`}>
      <button
        type="button"
        className={styles["forecast-toggle"]}
        onClick={() => setIsOpen((open) => !open)}
        aria-expanded={isOpen}
      >
        <span className={styles["forecast-heading"]}>Demand Forecast</span>
        {atRiskCount > 0 ? (
          <Badge tone="danger">{atRiskCount} need reorder</Badge>
        ) : (
          <Badge tone="success">Stock OK</Badge>
        )}
        <span className={styles["forecast-chevron"]} aria-hidden="true">
          <Icon name="chevron" size={16} />
        </span>
      </button>
      <div className={styles["forecast-body"]}>
        <div className={styles["forecast-hint"]}>
          Estimate based on the trailing 7-day average sold per day — not a guarantee.
        </div>
        <div className={styles["forecast-list"]}>
          {items.length === 0 && <div className={styles["forecast-empty"]}>No active products yet.</div>}
          {items.map((item) => (
            <div key={item.productId} className={styles["forecast-row"]}>
              <div className={styles["forecast-row-body"]}>
                <div className={styles["forecast-row-name"]}>{item.productName}</div>
                <div className={styles["forecast-row-sub"]}>{daysLabel(item.daysOfStockRemaining)}</div>
              </div>
              {item.atRisk && <Badge tone="danger">Reorder soon</Badge>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
