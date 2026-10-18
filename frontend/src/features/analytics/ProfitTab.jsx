import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { getOverview, getTopProducts } from "../../api/analytics";
import EmptyState from "../../components/EmptyState";
import LoadingState from "../../components/LoadingState";
import { useAuth } from "../auth/AuthContext";
import { formatPct, pesos } from "./analyticsFormat";
import styles from "./analytics.module.css";
import KpiTile from "./KpiTile";

function BreakdownRow({ label, cents, minus, total }) {
  if (minus && !cents) return null;
  return (
    <div className={`${styles["breakdown-row"]} ${minus ? styles["breakdown-minus"] : ""} ${total ? styles["breakdown-total"] : ""}`}>
      <span>{label}</span>
      <span>
        {minus && cents > 0 ? "−" : ""}
        {minus && cents < 0 ? "+" : ""}
        {pesos(minus ? Math.abs(cents) : cents)}
      </span>
    </div>
  );
}

export default function ProfitTab({ period }) {
  const { t } = useAuth();
  const overview = useQuery({ queryKey: ["analyticsOverview", period], queryFn: () => getOverview(period) });
  const top = useQuery({
    queryKey: ["analyticsTopProducts", period, "profit"],
    queryFn: () => getTopProducts({ ...period, sort: "profit", limit: 5 }),
  });

  if (overview.isLoading) return <LoadingState message={t("analytics.loading")} />;
  if (overview.isError) return <EmptyState message={t("analytics.loadError")} />;

  const { current, changePct } = overview.data;
  const coverage = current.costCoveragePct;
  const hasCostData = current.grossProfitCents != null;

  return (
    <div className={styles["tab-panel"]}>
      {coverage != null && coverage < 100 && (
        <div className={styles.notice}>
          <span>
            {hasCostData
              ? t("analytics.partialCost", { pct: formatPct(coverage) })
              : t("analytics.noCost")}{" "}
            <Link to="/inventory">{t("analytics.addCosts")}</Link>
          </span>
        </div>
      )}

      <div className={styles.kpis}>
        <KpiTile
          label={t("analytics.grossProfit")}
          value={pesos(current.grossProfitCents)}
          changePct={changePct.grossProfitCents}
          comparisonLabel={t("analytics.vsPrevious")}
        />
        <KpiTile label={t("analytics.grossMargin")} value={formatPct(current.grossMarginPct)} />
        <KpiTile label={t("analytics.cogs")} value={pesos(current.cogsCents)} />
        <KpiTile label={t("analytics.costCoverage")} value={formatPct(coverage)} />
      </div>

      <div className={styles.card}>
        <div className={styles["card-heading"]}>{t("analytics.breakdown")}</div>
        <div className={styles["card-hint"]}>{t("analytics.breakdownHint")}</div>
        <div className={styles.breakdown}>
          <BreakdownRow label={t("analytics.grossSales")} cents={current.grossSalesCents} />
          <BreakdownRow label={t("analytics.priceAdjustments")} cents={current.priceAdjustmentsCents} minus />
          <BreakdownRow label={t("analytics.discounts")} cents={current.discountsCents} minus />
          <BreakdownRow label={t("analytics.refunds")} cents={current.refundsCents} minus />
          <BreakdownRow label={t("analytics.netSales")} cents={current.netSalesCents} total />
          <BreakdownRow label={t("analytics.cogsCosted")} cents={current.cogsCents} minus />
          {hasCostData && <BreakdownRow label={t("analytics.grossProfit")} cents={current.grossProfitCents} total />}
        </div>
      </div>

      <div className={styles.card}>
        <div className={styles["card-heading"]}>{t("analytics.topByProfit")}</div>
        <div className={styles["card-hint"]}>{t("analytics.topByProfitHint")}</div>
        {top.data?.length === 0 && <div className={styles["card-empty"]}>{t("analytics.noSalesInRange")}</div>}
        <div className={styles.list}>
          {(top.data || []).map((product, index) => (
            <div key={product.productId} className={styles["list-row"]}>
              <span className={styles["list-rank"]}>{index + 1}</span>
              <div className={styles["list-body"]}>
                <span className={styles["list-name"]}>{product.productName}</span>
                <span className={styles["list-sub"]}>
                  {t("analytics.revenueLabel", { amount: pesos(product.revenueCents) })}
                </span>
              </div>
              <span className={styles["list-value"]}>
                {product.grossProfitCents == null ? t("analytics.noCostShort") : pesos(product.grossProfitCents)}
                {product.marginPct != null && (
                  <span className={styles["list-value-sub"]}>
                    {t("analytics.marginLabel", { pct: formatPct(product.marginPct) })}
                  </span>
                )}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
