import apiClient from "../lib/apiClient";

export async function createSale(payload) {
  const { data } = await apiClient.post("/sales", payload);
  return data;
}

export async function listSales({ range, sale_type, buyerId, page = 1, pageSize = 20 } = {}) {
  const { data } = await apiClient.get("/sales", {
    params: {
      range: range || undefined,
      sale_type: sale_type || undefined,
      buyer_id: buyerId || undefined,
      page,
      page_size: pageSize,
    },
  });
  return data;
}

export async function getSale(id) {
  const { data } = await apiClient.get(`/sales/${id}`);
  return data;
}

export async function getPublicReceipt(receiptCode) {
  const { data } = await apiClient.get(`/sales/receipt/${receiptCode}`);
  return data;
}

export async function searchBuyers(query) {
  const { data } = await apiClient.get("/sales/buyers/search", { params: { q: query } });
  return data;
}
