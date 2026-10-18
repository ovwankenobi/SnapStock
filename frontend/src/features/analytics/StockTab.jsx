import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { getInventoryHealth } from "../../api/analytics";
import Badge from "../../components/Badge";
import EmptyState from "../../components/EmptyState";
import LoadingState from "../../components/LoadingState";
import { useAuth } from "../auth/AuthContext";
import { formatDays, formatStockAmount, pesos } from "./analyticsFormat";
import styles from "./analytics.module.css";

const STATUS_ORDER = ["out_of_stock", "stockout_risk", "low", "slow_moving", "overstocked", "healthy"];
const STATUS_TONE = {
  out_of_stock: "danger",
  stockout_risk: "danger",
  low: "warning",
  slow_moving: "neutral",
  overstocked: "info",
  healthy: "success",
};
// Statuses where restocking is the next step.
const RESTOCK_STATUSES = new Set(["out_of_stock", "stockout_risk", "low"]);

function StockRow({ item, onRestock }) {
  const { t } = useAuth();
  const units = { unitType: item.unitType, unitLabel: item.unitLabel };
  const days = formatDays(item.daysRemaining);
  const facts = [
    t("analytics.inStock", { amount: formatStockAmount(item.stockPieces, units) }),
    days != null ? t("analytics.daysLeft", { days }) : null,
    item.turnover30 != null ? t("analytics.turnover", { value: item.turnover30 }) : null,
    item.stockValueCents != null ? t("analytics.stockValue", { amount: pesos(item.stockValueCents) }) : null,
  ].filter(Boolean);

  return (
    <div className={styles["list-row"]}>
      <div className={styles["list-body"]}>
        <span className={styles["list-name"]}>{item.productName}</span>
        <span className={styles["list-sub"]}>{facts.join(" · ")}</span>
        {item.suggestedReorderPieces > 0 && (
          <span className={styles["list-sub"]}>
            {t("analytics.suggestedReorder", { amount: formatStockAmount(item.suggestedReorderPieces, units) })}
          </span>
        )}
      </div>
      {RESTOCK_STATUSES.has(item.status) && (
        <button type="button" className={styles["list-action"]} onClick={onRestock}>
          {t("analytics.restock")}
        </button>
      )}
    </div>
  );
}

export default function StockTab() {
  const { t } = useAuth();
  const navigate = useNavigate();
  const { data, isLoading, isError } = useQuery({ queryKey: ["analyticsInventory"], queryFn: getInventoryHealth });

  if (isLoading) return <LoadingState message={t("analytics.loading")} />;
  if (isError) return <EmptyState message={t("analytics.loadError")} />;
  if (data.length === 0) return <EmptyState message={t("analytics.noProducts")} />;

  const groups = STATUS_ORDER.map((status) => ({ status, items: data.filter((item) => item.status === status) })).filter(
    (group) => group.items.length > 0,
  );
  const totalValue = data.reduce((sum, item) => sum + (item.stockValueCents || 0), 0);
  const openRestock = () => navigate("/inventory", { state: { view: "restock" } });

  return (
    <div className={styles["tab-panel"]}>
      <div className={styles.kpis}>
        <div className={styles.kpi}>
          <div className={styles["kpi-label"]}>{t("analytics.needAttention")}</div>
          <div className={styles["kpi-value"]}>
            {data.filter((item) => RESTOCK_STATUSES.has(item.status)).length}
          </div>
        </div>
        <div className={styles.kpi}>
          <div className={styles["kpi-label"]}>{t("analytics.stockValueTotal")}</div>
          <div className={styles["kpi-value"]}>{totalValue ? pesos(totalValue) : "—"}</div>
        </div>
      </div>

      {groups.map((group) => (
        <div key={group.status} className={styles.card}>
          <div className={styles["group-heading"]}>
            <Badge tone={STATUS_TONE[group.status]}>{t(`analytics.status.${group.status}`)}</Badge>
            <span>{group.items.length}</span>
          </div>
          <div className={styles["card-hint"]}>{t(`analytics.statusHint.${group.status}`)}</div>
          <div className={styles.list}>
            {group.items.map((item) => (
              <StockRow key={item.productId} item={item} onRestock={openRestock} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
