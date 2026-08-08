import axios from "axios";

export const API_ORIGIN = new URL(import.meta.env.VITE_API_URL).origin;

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

const AUTH_ENDPOINTS = ["/auth/login", "/auth/register"];

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const isAuthEndpoint = AUTH_ENDPOINTS.some((path) => error.config?.url?.includes(path));
    if (error.response?.status === 401 && !isAuthEndpoint) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

export default apiClient;
