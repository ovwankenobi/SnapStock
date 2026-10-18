import apiClient from "../lib/apiClient";

export async function listPayoutAccounts() {
  const { data } = await apiClient.get("/seller/payout-accounts");
  return data;
}

export async function createPayoutAccount(payload) {
  const { data } = await apiClient.post("/seller/payout-accounts", payload);
  return data;
}

export async function updatePayoutAccount(id, payload) {
  const { data } = await apiClient.patch(`/seller/payout-accounts/${id}`, payload);
  return data;
}

export async function deletePayoutAccount(id) {
  await apiClient.delete(`/seller/payout-accounts/${id}`);
}

export async function uploadPayoutQr(id, file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post(`/seller/payout-accounts/${id}/qr`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

// Creates or updates the account, then uploads its QR, since the upload needs the account's id.
export async function savePayoutAccount({ id, values, qrFile }) {
  const account = id ? await updatePayoutAccount(id, values) : await createPayoutAccount(values);
  return qrFile ? uploadPayoutQr(account.id, qrFile) : account;
}
