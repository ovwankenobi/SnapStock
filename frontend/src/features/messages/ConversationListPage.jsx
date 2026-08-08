import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { listConversations } from "../../api/messages";
import AppLayout from "../../components/AppLayout";
import ConversationRow from "../../components/ConversationRow";
import EmptyState from "../../components/EmptyState";
import { useAuth } from "../auth/AuthContext";
import { formatShortTimestamp } from "../sales/salesFormat";
import { buyerNavItems, sellerNavItems } from "../../lib/nav";
import styles from "./messages.module.css";

export default function ConversationListPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
    refetchInterval: 8000,
  });

  const conversations = data?.items || [];
  const navItems = user?.role === "seller" ? sellerNavItems() : buyerNavItems();

  return (
    <AppLayout navItems={navItems} title="Messages">
      <div className={styles["list-page"]}>
        {isLoading && <p className={styles.hint}>Loading conversations...</p>}
        {isError && <EmptyState message="Could not load your conversations." />}
        {!isLoading && !isError && conversations.length === 0 && (
          <EmptyState message="No conversations yet." />
        )}
        {conversations.map((conversation) => (
          <ConversationRow
            key={conversation.id}
            name={conversation.otherUser.fullName}
            lastMessage={conversation.lastMessagePreview || "No messages yet"}
            timeLabel={formatShortTimestamp(conversation.lastMessageAt)}
            unreadCount={conversation.unreadCount}
            active={false}
            onOpen={() => navigate(`/messages/${conversation.id}`)}
          />
        ))}
      </div>
    </AppLayout>
  );
}
