import apiClient from "../lib/apiClient";

export async function listProducts({ search, category, stockStatus, page = 1, pageSize = 20 } = {}) {
  const { data } = await apiClient.get("/products", {
    params: {
      search: search || undefined,
      category: category || undefined,
      stock_status: stockStatus || undefined,
      page,
      page_size: pageSize,
    },
  });
  return data;
}

export async function getLowStockProducts() {
  const { data } = await apiClient.get("/products/low-stock");
  return data;
}

export async function getProduct(id) {
  const { data } = await apiClient.get(`/products/${id}`);
  return data;
}

export async function createProduct(payload) {
  const { data } = await apiClient.post("/products", payload);
  return data;
}

export async function updateProduct(id, payload) {
  const { data } = await apiClient.patch(`/products/${id}`, payload);
  return data;
}

export async function deleteProduct(id) {
  await apiClient.delete(`/products/${id}`);
}

export async function quickSellProduct(id, payload) {
  const { data } = await apiClient.post(`/products/${id}/quick-sell`, payload);
  return data;
}

export async function restockProduct(id, payload) {
  const { data } = await apiClient.post(`/products/${id}/restock`, payload);
  return data;
}

export async function uploadProductPhoto(id, file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post(`/products/${id}/photo`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}
