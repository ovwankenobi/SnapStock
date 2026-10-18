import { MEASURE_SCALE, centsToPeso, isMeasured, unitSuffix } from "../../lib/format";

// A stock-piece amount (thousandths for measure products) as "12 pcs" / "1.5 kg".
export function formatStockAmount(pieces, { unitType, unitLabel }) {
  if (pieces == null) return "—";
  if (isMeasured(unitType)) {
    return `${Number((pieces / MEASURE_SCALE).toFixed(1))} ${unitSuffix(unitType, unitLabel)}`;
  }
  const rounded = Number(pieces.toFixed(pieces < 10 ? 1 : 0));
  return `${rounded} pc${rounded === 1 ? "" : "s"}`;
}

export function formatPct(value) {
  if (value == null) return "—";
  return `${Number(value.toFixed(1))}%`;
}

export function formatDays(days) {
  if (days == null) return null;
  return days < 1 ? "<1" : String(Math.round(days));
}

// "+12% vs previous" with a tone that knows whether up is good for this metric.
export function deltaInfo(changePct, { upIsGood = true } = {}) {
  if (changePct == null) return null;
  const sign = changePct > 0 ? "+" : "";
  const tone = changePct === 0 ? "neutral" : (changePct > 0) === upIsGood ? "good" : "bad";
  return { label: `${sign}${Number(changePct.toFixed(1))}%`, tone };
}

export const pesos = (cents) => (cents == null ? "—" : centsToPeso(cents));

// Compact peso amounts for chart axes and tooltips with tight space.
export function compactPesos(cents) {
  const pesosValue = (cents || 0) / 100;
  if (Math.abs(pesosValue) >= 1000) {
    return `₱${new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(pesosValue)}`;
  }
  return `₱${Math.round(pesosValue)}`;
}
