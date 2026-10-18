import { centsToPeso } from "../../lib/format";
import { formatStockAmount } from "./analyticsFormat";

const WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

// Turns the backend's raw figures into the display values the insight templates expect.
function displayParams(t, insight) {
  const p = insight.params || {};
  const out = { ...p };
  for (const [key, value] of Object.entries(p)) {
    if (key.endsWith("Cents") && typeof value === "number") out[key] = centsToPeso(value);
  }
  if (p.pct != null) out.pct = `${Math.abs(p.pct)}%`;
  if (p.weekday != null) out.weekday = t(`analytics.weekdays.${WEEKDAY_KEYS[p.weekday]}`);
  if (p.reorderPieces != null) {
    out.reorder = formatStockAmount(p.reorderPieces, { unitType: p.unitType, unitLabel: p.unitLabel });
  }
  return out;
}

export function insightTitle(t, insight) {
  return t(`insights.${insight.code}.title`, displayParams(t, insight));
}

export function insightBody(t, insight) {
  return t(`insights.${insight.code}.body`, displayParams(t, insight));
}

export function insightAction(t, insight) {
  return t(`insights.actions.${insight.action}`);
}

export const SEVERITY_TONE = { high: "danger", medium: "warning", low: "info" };
