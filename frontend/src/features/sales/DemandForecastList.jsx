import Badge from "../../components/Badge";
import styles from "./sales.module.css";

function daysLabel(days) {
  if (days == null) return "Not enough sales history yet";
  const rounded = Math.round(days);
  if (rounded < 1) return "Could run out today";
  return `~${rounded} day${rounded === 1 ? "" : "s"} of stock left`;
}

export default function DemandForecastList({ forecasts }) {
  const items = [...(forecasts || [])].sort((a, b) => {
    const aDays = a.daysOfStockRemaining ?? Infinity;
    const bDays = b.daysOfStockRemaining ?? Infinity;
    return aDays - bDays;
  });

  return (
    <div className={styles["forecast-card"]}>
      <div className={styles["forecast-heading"]}>Demand Forecast</div>
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
  );
}
