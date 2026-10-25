import apiClient from "../lib/apiClient";

export async function createSale(payload) {
  const { data } = await apiClient.post("/sales", payload);
  return data;
}

export async function listSales({
  range,
  start,
  end,
  sale_type,
  paymentMethod,
  buyerId,
  status,
  page = 1,
  pageSize = 20,
} = {}) {
  const { data } = await apiClient.get("/sales", {
    params: {
      range: range || undefined,
      start: start || undefined,
      end: end || undefined,
      sale_type: sale_type || undefined,
      payment_method: paymentMethod || undefined,
      buyer_id: buyerId || undefined,
      status: status || undefined,
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

export async function voidSale(id, reason) {
  const { data } = await apiClient.post(`/sales/${id}/void`, { reason: reason || undefined });
  return data;
}

export async function refundSale(id, reason) {
  const { data } = await apiClient.post(`/sales/${id}/refund`, { reason: reason || undefined });
  return data;
}

export async function confirmPayment(id) {
  const { data } = await apiClient.post(`/sales/${id}/confirm-payment`);
  return data;
}

export async function uploadSaleProof(id, file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post(`/sales/${id}/proof`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function rejectOrder(id, reason) {
  const { data } = await apiClient.post(`/sales/${id}/reject`, { reason: reason || undefined });
  return data;
}
