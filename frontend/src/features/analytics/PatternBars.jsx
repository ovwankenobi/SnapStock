import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { centsToPeso } from "../../lib/format";
import { compactPesos } from "./analyticsFormat";
import styles from "./analytics.module.css";

function PatternTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className={styles["chart-tooltip"]}>
      <div className={styles["chart-tooltip-label"]}>{point.fullLabel}</div>
      <div className={styles["chart-tooltip-value"]}>{centsToPeso(point.avgRevenueCents)}</div>
      <div className={styles["chart-tooltip-label"]}>{point.avgTransactions} sales on average</div>
    </div>
  );
}

// Average net sales per weekday or hour: a single series, so the card title names it.
export default function PatternBars({ title, subtitle, data, height = 160 }) {
  const peak = Math.max(0, ...data.map((d) => d.avgRevenueCents));
  return (
    <div className={styles.card}>
      <div className={styles["card-heading"]}>{title}</div>
      {subtitle && <div className={styles["card-hint"]}>{subtitle}</div>}
      {peak === 0 ? (
        <div className={styles["card-empty"]}>Not enough sales yet.</div>
      ) : (
        <ResponsiveContainer width="100%" height={height}>
          <BarChart data={data} margin={{ top: 8, right: 4, left: 0, bottom: 0 }} barCategoryGap="20%">
            <CartesianGrid vertical={false} stroke="var(--color-border)" />
            <XAxis
              dataKey="label"
              tick={{ fill: "var(--color-muted)", fontSize: 11 }}
              axisLine={{ stroke: "var(--color-border)" }}
              tickLine={false}
              interval="preserveStartEnd"
              minTickGap={4}
            />
            <YAxis
              width={44}
              tick={{ fill: "var(--color-muted)", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={compactPesos}
              tickCount={3}
            />
            <Tooltip content={<PatternTooltip />} cursor={{ fill: "var(--color-surface-alt)" }} />
            <Bar dataKey="avgRevenueCents" fill="var(--color-primary)" radius={[4, 4, 0, 0]} maxBarSize={24} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
