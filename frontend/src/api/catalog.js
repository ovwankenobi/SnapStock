import apiClient from "../lib/apiClient";

export async function listCatalogProducts({ search, category, sellerId, page = 1, pageSize = 24 } = {}) {
  const { data } = await apiClient.get("/catalog/products", {
    params: {
      search: search || undefined,
      category: category || undefined,
      seller_id: sellerId || undefined,
      page,
      page_size: pageSize,
    },
  });
  return data;
}

export async function getCatalogProduct(id) {
  const { data } = await apiClient.get(`/catalog/products/${id}`);
  return data;
}

export async function getCatalogSeller(id) {
  const { data } = await apiClient.get(`/catalog/sellers/${id}`);
  return data;
}

export async function searchCatalogByImage({ file, query }) {
  const form = new FormData();
  form.append("file", file);
  form.append("query", query);
  const { data } = await apiClient.post("/catalog/search-by-image", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function buyProduct(productId, payload) {
  const { data } = await apiClient.post(`/catalog/products/${productId}/order`, payload);
  return data;
}

export async function getMyReceipts({ page = 1, pageSize = 20 } = {}) {
  const { data } = await apiClient.get("/me/receipts", { params: { page, page_size: pageSize } });
  return data;
}
