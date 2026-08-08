import apiClient from "../lib/apiClient";

export async function getSummary() {
  const { data } = await apiClient.get("/analytics/summary");
  return data;
}

export async function getTopProducts({ range = "week", limit = 5 } = {}) {
  const { data } = await apiClient.get("/analytics/top-products", { params: { range, limit } });
  return data;
}

export async function getSalesTrend({ range = "week" } = {}) {
  const { data } = await apiClient.get("/analytics/sales-trend", { params: { range } });
  return data;
}

export async function getForecast() {
  const { data } = await apiClient.get("/analytics/forecast");
  return data;
}
