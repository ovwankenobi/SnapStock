import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { centsToPeso } from "../../lib/format";
import styles from "./dashboard.module.css";

function formatDayLabel(isoDate) {
  return new Intl.DateTimeFormat(undefined, { weekday: "short" }).format(new Date(`${isoDate}T00:00:00`));
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className={styles["trend-tooltip"]}>
      <div className={styles["trend-tooltip-date"]}>{label}</div>
      <div className={styles["trend-tooltip-value"]}>{centsToPeso(payload[0].value)}</div>
    </div>
  );
}

export default function SalesTrendChart({ points }) {
  const data = (points || []).map((point) => ({ ...point, label: formatDayLabel(point.date) }));

  return (
    <div className={styles["trend-card"]}>
      <div className={styles["trend-heading"]}>Sales Trend</div>
      <ResponsiveContainer width="100%" height={180}>
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
          />
          <YAxis hide />
          <Tooltip content={<ChartTooltip />} />
          <Area
            type="monotone"
            dataKey="revenueCents"
            stroke="var(--color-primary)"
            strokeWidth={2}
            fill="url(#dashboardTrendFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
