import apiClient from "../lib/apiClient";

export async function login(email, password) {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  const { data } = await apiClient.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
}

export async function register(payload) {
  const { data } = await apiClient.post("/auth/register", payload);
  return data;
}

export async function getMe() {
  const { data } = await apiClient.get("/auth/me");
  return data;
}

export async function updateMe(payload) {
  const { data } = await apiClient.patch("/auth/me", payload);
  return data;
}

export async function requestPasswordReset(email) {
  const { data } = await apiClient.post("/auth/forgot-password", { email });
  return data;
}

export async function resetPassword(token, newPassword) {
  await apiClient.post("/auth/reset-password", { token, newPassword });
}

export async function requestPasswordChange() {
  await apiClient.post("/auth/change-password");
}

export async function qrLogin(key) {
  const { data } = await apiClient.post("/auth/qr-login", { key });
  return data;
}

export async function createQrLoginKey(currentPassword) {
  const { data } = await apiClient.post("/auth/qr-login-key", { currentPassword });
  return data;
}

export async function revokeQrLoginKey() {
  await apiClient.delete("/auth/qr-login-key");
}
