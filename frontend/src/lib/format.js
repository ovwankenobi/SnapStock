import { API_ORIGIN } from "./apiClient";

const AVATAR_PALETTE = ["#C4571E", "#2C5FAE", "#2F9E5B", "#8C3A2E", "#B8791A"];

const UNIT_SUFFIX = { piece: "pc", bundle: "bundle" };

// Measure products store stock/quantities in thousandths of their unit (see unit-conversion docs).
export const MEASURE_SCALE = 1000;

export function mediaUrl(path) {
  if (!path) return null;
  return path.startsWith("http") ? path : `${API_ORIGIN}${path}`;
}

export function centsToPeso(cents) {
  return "₱" + Math.round(cents / 100).toLocaleString();
}

export function isMeasured(unitType) {
  return unitType === "measure";
}

export function unitSuffix(unitType, unitLabel) {
  if (isMeasured(unitType)) return unitLabel || "unit";
  return UNIT_SUFFIX[unitType] || unitType;
}

// Stored integer quantity -> display string ("1.5" for 1500 milli-units of a measure product).
export function formatQuantity(unitType, quantity) {
  if (!isMeasured(unitType)) return String(quantity);
  return String(Number(((quantity || 0) / MEASURE_SCALE).toFixed(3)));
}

// Display/input string -> stored integer quantity.
export function parseQuantityInput(value, unitType) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) return 0;
  return isMeasured(unitType) ? Math.round(number * MEASURE_SCALE) : Math.floor(number);
}

// Keeps digits and a single decimal point with at most 3 decimals (measure) or digits only.
export function sanitizeQuantityInput(value, unitType) {
  if (!isMeasured(unitType)) return value.replace(/[^0-9]/g, "");
  const [whole, ...rest] = value.replace(/[^0-9.]/g, "").split(".");
  return rest.length ? `${whole}.${rest.join("").slice(0, 3)}` : whole;
}

// Mirrors backend services.inventory.line_total_cents (half-up integer rounding).
export function lineTotalCents(priceCents, quantity, unitType) {
  const scale = isMeasured(unitType) ? MEASURE_SCALE : 1;
  return Math.floor((quantity * priceCents * 2 + scale) / (2 * scale));
}

export function initials(name) {
  return (name || "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}

export function colorForKey(key) {
  const str = String(key || "");
  let hash = 0;
  for (let i = 0; i < str.length; i++) hash = (hash + str.charCodeAt(i)) % AVATAR_PALETTE.length;
  return AVATAR_PALETTE[hash];
}

// Peso text input ("12.50") <-> integer cents. Returns null for blank/invalid input.
export function pesoInputToCents(value) {
  if (value == null || String(value).trim() === "") return null;
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) return null;
  return Math.round(number * 100);
}

export function centsToPesoInput(cents) {
  if (cents == null) return "";
  return cents % 100 === 0 ? String(cents / 100) : (cents / 100).toFixed(2);
}

// Keeps digits and one decimal point with at most 2 decimals.
export function sanitizePesoInput(value) {
  const [whole, ...rest] = value.replace(/[^0-9.]/g, "").split(".");
  return rest.length ? `${whole}.${rest.join("").slice(0, 2)}` : whole;
}
