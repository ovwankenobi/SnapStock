import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatDate } from "../../lib/dates";
import { centsToPeso } from "../../lib/format";
import styles from "./dashboard.module.css";

function bucketLabel(isoDate, granularity, pointCount) {
  if (granularity === "month") return formatDate(isoDate, { month: "short" });
  if (granularity === "day" && pointCount <= 7) return formatDate(isoDate, { weekday: "short" });
  return formatDate(isoDate, { month: "short", day: "numeric" });
}

function tooltipLabel(isoDate, granularity) {
  if (granularity === "month") return formatDate(isoDate, { month: "long", year: "numeric" });
  const day = formatDate(isoDate, { weekday: "short", month: "short", day: "numeric" });
  return granularity === "week" ? `Week of ${day}` : day;
}

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className={styles["trend-tooltip"]}>
      <div className={styles["trend-tooltip-date"]}>{point.tooltipLabel}</div>
      <div className={styles["trend-tooltip-value"]}>{centsToPeso(point.revenueCents)}</div>
      <div className={styles["trend-tooltip-date"]}>
        {point.saleCount} sale{point.saleCount === 1 ? "" : "s"}
      </div>
    </div>
  );
}

// Net sales per bucket (one series, so no legend — the title names it).
export default function SalesTrendChart({ points, granularity = "day", title = "Sales Trend", height = 180 }) {
  const list = points || [];
  const data = list.map((point) => ({
    ...point,
    label: bucketLabel(point.date, granularity, list.length),
    tooltipLabel: tooltipLabel(point.date, granularity),
  }));

  return (
    <div className={styles["trend-card"]}>
      <div className={styles["trend-heading"]}>{title}</div>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="dashboardTrendFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-primary)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--color-primary)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke="var(--color-border)" />
          <XAxis
            dataKey="label"
            tick={{ fill: "var(--color-muted)", fontSize: 11 }}
            axisLine={{ stroke: "var(--color-border)" }}
            tickLine={false}
            interval="preserveStartEnd"
            minTickGap={12}
          />
          <YAxis hide />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: "var(--color-muted)", strokeWidth: 1 }} />
          <Area
            type="monotone"
            dataKey="revenueCents"
            stroke="var(--color-primary)"
            strokeWidth={2}
            fill="url(#dashboardTrendFill)"
            activeDot={{ r: 4, stroke: "var(--color-surface)", strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
