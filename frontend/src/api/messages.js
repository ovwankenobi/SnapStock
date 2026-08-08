import apiClient from "../lib/apiClient";

export async function listConversations() {
  const { data } = await apiClient.get("/conversations");
  return data;
}

export async function createConversation({ otherUserId, productId } = {}) {
  const { data } = await apiClient.post("/conversations", {
    otherUserId,
    productId: productId || undefined,
  });
  return data;
}

export async function listMessages(conversationId, { page = 1, pageSize = 30 } = {}) {
  const { data } = await apiClient.get(`/conversations/${conversationId}/messages`, {
    params: { page, page_size: pageSize },
  });
  return data;
}

export async function sendMessage(conversationId, body) {
  const { data } = await apiClient.post(`/conversations/${conversationId}/messages`, { body });
  return data;
}

export async function markConversationRead(conversationId) {
  await apiClient.post(`/conversations/${conversationId}/read`);
}
