import apiClient from "../lib/apiClient";

// `range` is today | week | month | custom; custom also takes `start`/`end` as local "YYYY-MM-DD" dates.
function rangeParams({ range = "week", start, end } = {}) {
  return range === "custom" ? { range, start, end } : { range };
}

export async function getSummary() {
  const { data } = await apiClient.get("/analytics/summary");
  return data;
}

export async function getOverview(period) {
  const { data } = await apiClient.get("/analytics/overview", { params: rangeParams(period) });
  return data;
}

export async function getTopProducts({ limit = 5, sort = "revenue", ...period } = {}) {
  const { data } = await apiClient.get("/analytics/top-products", {
    params: { ...rangeParams(period), limit, sort },
  });
  return data;
}

export async function getSalesTrend({ granularity = "day", ...period } = {}) {
  const { data } = await apiClient.get("/analytics/sales-trend", {
    params: { ...rangeParams(period), granularity },
  });
  return data;
}

export async function getPatterns({ weeks = 8 } = {}) {
  const { data } = await apiClient.get("/analytics/patterns", { params: { weeks } });
  return data;
}

export async function getInventoryHealth() {
  const { data } = await apiClient.get("/analytics/inventory");
  return data;
}

export async function getForecast() {
  const { data } = await apiClient.get("/analytics/forecast");
  return data;
}

export async function getInsights() {
  const { data } = await apiClient.get("/analytics/insights");
  return data;
}
