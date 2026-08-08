import { useQuery } from "@tanstack/react-query";

import { listConversations } from "../api/messages";
import { useAuth } from "../features/auth/AuthContext";

export function useUnreadMessageCount() {
  const { token } = useAuth();
  const { data } = useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
    enabled: !!token,
    refetchInterval: 15000,
  });
  return (data?.items || []).reduce((sum, c) => sum + c.unreadCount, 0);
}
