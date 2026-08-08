import { API_ORIGIN } from "./apiClient";

const AVATAR_PALETTE = ["#C4571E", "#2C5FAE", "#2F9E5B", "#8C3A2E", "#B8791A"];

const UNIT_SUFFIX = { piece: "pc", bundle: "bundle", grams: "kg" };

export function mediaUrl(path) {
  if (!path) return null;
  return path.startsWith("http") ? path : `${API_ORIGIN}${path}`;
}

export function centsToPeso(cents) {
  return "₱" + Math.round(cents / 100).toLocaleString();
}

export function unitSuffix(unitType) {
  return UNIT_SUFFIX[unitType] || unitType;
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
