import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getOverview, getPatterns, getSalesTrend, getTopProducts } from "../../api/analytics";
import EmptyState from "../../components/EmptyState";
import LoadingState from "../../components/LoadingState";
import SegmentedControl from "../../components/SegmentedControl";
import { formatQuantity, isMeasured, unitSuffix } from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import SalesTrendChart from "../dashboard/SalesTrendChart";
import { pesos } from "./analyticsFormat";
import styles from "./analytics.module.css";
import KpiTile from "./KpiTile";
import PatternBars from "./PatternBars";

const WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

function daysInPeriod(period) {
  if (period.range === "today") return 1;
  if (period.range === "week") return 7;
  if (period.range === "month") return 30;
  return Math.round((new Date(period.end) - new Date(period.start)) / 86_400_000) + 1;
}

// Keep the chart readable: daily up to a month, weekly up to ~4 months, monthly beyond.
function granularityFor(days) {
  if (days <= 31) return "day";
  if (days <= 120) return "week";
  return "month";
}

function hourLabel(hour) {
  const suffix = hour < 12 ? "a" : "p";
  return `${hour % 12 || 12}${suffix}`;
}

export function quantityLabel(product) {
  const qty = formatQuantity(product.unitType, product.quantitySold);
  return isMeasured(product.unitType) ? `${qty} ${unitSuffix(product.unitType, product.unitLabel)}` : `${qty} sold`;
}

export default function SalesTab({ period }) {
  const { t } = useAuth();
  const [topSort, setTopSort] = useState("revenue");

  // A single day makes a one-point chart, so "Today" charts the last 7 days instead.
  const trendPeriod = period.range === "today" ? { range: "week" } : period;
  const granularity = granularityFor(daysInPeriod(trendPeriod));

  const overview = useQuery({ queryKey: ["analyticsOverview", period], queryFn: () => getOverview(period) });
  const trend = useQuery({
    queryKey: ["analyticsSalesTrend", trendPeriod, granularity],
    queryFn: () => getSalesTrend({ ...trendPeriod, granularity }),
  });
  const top = useQuery({
    queryKey: ["analyticsTopProducts", period, topSort],
    queryFn: () => getTopProducts({ ...period, sort: topSort, limit: 5 }),
  });
  const patterns = useQuery({ queryKey: ["analyticsPatterns", 8], queryFn: () => getPatterns({ weeks: 8 }) });

  if (overview.isLoading) return <LoadingState message={t("analytics.loading")} />;
  if (overview.isError) return <EmptyState message={t("analytics.loadError")} />;

  const { current, changePct } = overview.data;
  const vs = t("analytics.vsPrevious");

  return (
    <div className={styles["tab-panel"]}>
      <div className={styles.kpis}>
        <KpiTile
          label={t("analytics.netSales")}
          value={pesos(current.netSalesCents)}
          changePct={changePct.netSalesCents}
          comparisonLabel={vs}
        />
        <KpiTile
          label={t("analytics.transactions")}
          value={current.transactions.toLocaleString()}
          changePct={changePct.transactions}
          comparisonLabel={vs}
        />
        <KpiTile
          label={t("analytics.unitsSold")}
          value={Number(current.unitsSold.toFixed(1)).toLocaleString()}
          changePct={changePct.unitsSold}
          comparisonLabel={vs}
        />
        <KpiTile
          label={t("analytics.avgTransaction")}
          value={pesos(current.avgTransactionCents)}
          changePct={changePct.avgTransactionCents}
          comparisonLabel={vs}
        />
      </div>

      <SalesTrendChart
        points={trend.data}
        granularity={granularity}
        title={period.range === "today" ? t("analytics.trendLast7") : t(`analytics.trendBy.${granularity}`)}
      />

      <div className={styles.card}>
        <div className={styles["toggle-row"]}>
          <div className={styles["card-heading"]}>{t("analytics.topProducts")}</div>
          <SegmentedControl
            options={[
              { value: "revenue", label: t("analytics.byRevenue") },
              { value: "quantity", label: t("analytics.byQuantity") },
            ]}
            value={topSort}
            onChange={setTopSort}
          />
        </div>
        {top.data?.length === 0 && <div className={styles["card-empty"]}>{t("analytics.noSalesInRange")}</div>}
        <div className={styles.list}>
          {(top.data || []).map((product, index) => (
            <div key={product.productId} className={styles["list-row"]}>
              <span className={styles["list-rank"]}>{index + 1}</span>
              <div className={styles["list-body"]}>
                <span className={styles["list-name"]}>{product.productName}</span>
                <span className={styles["list-sub"]}>{quantityLabel(product)}</span>
              </div>
              <span className={styles["list-value"]}>{pesos(product.revenueCents)}</span>
            </div>
          ))}
        </div>
      </div>

      {patterns.data && (
        <div className={styles["grid-2"]}>
          <PatternBars
            title={t("analytics.byWeekday")}
            subtitle={t("analytics.patternHint", { weeks: 8 })}
            data={patterns.data.weekdays.map((d) => ({
              ...d,
              label: t(`analytics.weekdays.${WEEKDAY_KEYS[d.weekday]}`),
              fullLabel: t(`analytics.weekdays.${WEEKDAY_KEYS[d.weekday]}`),
            }))}
          />
          <PatternBars
            title={t("analytics.byHour")}
            subtitle={t("analytics.patternHint", { weeks: 8 })}
            // Trim the empty overnight hours so the trading day fills the width.
            data={trimHours(patterns.data.hours).map((h) => ({
              ...h,
              label: hourLabel(h.hour),
              fullLabel: `${hourLabel(h.hour)}m`,
            }))}
          />
        </div>
      )}
    </div>
  );
}

function trimHours(hours) {
  const active = hours.filter((h) => h.avgTransactions > 0);
  if (active.length === 0) return hours;
  const first = Math.max(0, active[0].hour - 1);
  const last = Math.min(23, active[active.length - 1].hour + 1);
  return hours.filter((h) => h.hour >= first && h.hour <= last);
}
