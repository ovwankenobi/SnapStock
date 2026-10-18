import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getForecast } from "../../api/analytics";
import Badge from "../../components/Badge";
import EmptyState from "../../components/EmptyState";
import LoadingState from "../../components/LoadingState";
import SegmentedControl from "../../components/SegmentedControl";
import { useAuth } from "../auth/AuthContext";
import { formatDays, formatPct, formatStockAmount } from "./analyticsFormat";
import styles from "./analytics.module.css";

const CONFIDENCE_TONE = { high: "success", medium: "info", low: "neutral" };

export default function ForecastTab() {
  const { t } = useAuth();
  const [horizon, setHorizon] = useState(7);
  const { data, isLoading, isError } = useQuery({ queryKey: ["analyticsForecast"], queryFn: getForecast });

  if (isLoading) return <LoadingState message={t("analytics.loading")} />;
  if (isError) return <EmptyState message={t("analytics.loadError")} />;
  if (data.items.length === 0) return <EmptyState message={t("analytics.noProducts")} />;

  const atRisk = data.items.filter((item) => item.atRisk).length;

  return (
    <div className={styles["tab-panel"]}>
      <div className={styles.kpis}>
        <div className={styles.kpi}>
          <div className={styles["kpi-label"]}>{t("analytics.forecastAccuracy")}</div>
          <div className={styles["kpi-value"]}>{formatPct(data.accuracyPct)}</div>
          <div className={styles["kpi-delta"]}>{t("analytics.forecastAccuracyHint")}</div>
        </div>
        <div className={styles.kpi}>
          <div className={styles["kpi-label"]}>{t("analytics.runOutWithinWeek")}</div>
          <div className={styles["kpi-value"]}>{atRisk}</div>
        </div>
      </div>

      <div className={styles.card}>
        <div className={styles["toggle-row"]}>
          <div className={styles["card-heading"]}>{t("analytics.expectedDemand")}</div>
          <SegmentedControl
            options={[
              { value: 7, label: t("analytics.next7") },
              { value: 14, label: t("analytics.next14") },
            ]}
            value={horizon}
            onChange={setHorizon}
          />
        </div>
        <div className={styles["card-hint"]}>
          {data.weekdayAdjusted ? t("analytics.forecastMethodWeekday") : t("analytics.forecastMethod")}
        </div>
        <div className={styles.list}>
          {data.items.map((item) => {
            const units = { unitType: item.unitType, unitLabel: item.unitLabel };
            const demand = horizon === 7 ? item.forecast7 : item.forecast14;
            const days = formatDays(item.daysOfStockRemaining);
            return (
              <div key={item.productId} className={styles["list-row"]}>
                <div className={styles["list-body"]}>
                  <span className={styles["list-name"]}>{item.productName}</span>
                  <span className={styles["list-sub"]}>
                    {item.method === "none"
                      ? t("analytics.noSalesYet")
                      : [
                          t("analytics.inStock", { amount: formatStockAmount(item.stockPieces, units) }),
                          days != null ? t("analytics.daysLeft", { days }) : null,
                          item.method === "fallback" ? t("analytics.fallbackNote") : null,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                  </span>
                </div>
                <span className={styles["list-value"]}>
                  {demand == null ? "—" : formatStockAmount(demand, units)}
                  <span className={styles["list-value-sub"]}>
                    {item.atRisk ? (
                      <Badge tone="danger">{t("analytics.reorderSoon")}</Badge>
                    ) : (
                      <Badge tone={CONFIDENCE_TONE[item.confidence]}>
                        {t(`analytics.confidence.${item.confidence}`)}
                      </Badge>
                    )}
                  </span>
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
