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

export async function getProductCategories() {
  const { data } = await apiClient.get("/products/categories");
  return data;
}

export async function deleteProductCategory(name) {
  await apiClient.delete("/products/categories", { params: { name } });
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

export async function searchProductsByImage({ file, query }) {
  const form = new FormData();
  form.append("file", file);
  form.append("query", query);
  const { data } = await apiClient.post("/products/search-by-image", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function bulkRestockProducts(payload) {
  const { data } = await apiClient.post("/products/restock", payload);
  return data;
}
