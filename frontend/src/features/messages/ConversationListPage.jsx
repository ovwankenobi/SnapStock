import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { listConversations } from "../../api/messages";
import AppLayout from "../../components/AppLayout";
import ConversationRow from "../../components/ConversationRow";
import EmptyState from "../../components/EmptyState";
import SearchField from "../../components/SearchField";
import { useAuth } from "../auth/AuthContext";
import { formatShortTimestamp } from "../sales/salesFormat";
import { buyerNavItems, sellerNavItems } from "../../lib/nav";
import styles from "./messages.module.css";

export default function ConversationListPage() {
  const { user, t } = useAuth();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
    refetchInterval: 8000,
  });

  const conversations = data?.items || [];
  const trimmedQuery = query.trim().toLowerCase();
  const visibleConversations = trimmedQuery
    ? conversations.filter((conversation) =>
        (conversation.otherUser.fullName || "").toLowerCase().includes(trimmedQuery),
      )
    : conversations;
  const navItems = user?.role === "seller" ? sellerNavItems() : buyerNavItems();

  return (
    <AppLayout navItems={navItems} title="Messages">
      <div className={styles["list-page"]}>
        {conversations.length > 0 && (
          <div className={styles["list-search"]}>
            <SearchField value={query} onChange={setQuery} placeholder={t("messages.searchPlaceholder")} />
          </div>
        )}
        {isLoading && <p className={styles.hint}>Loading conversations...</p>}
        {isError && <EmptyState message="Could not load your conversations." />}
        {!isLoading && !isError && conversations.length === 0 && (
          <EmptyState message="No conversations yet." />
        )}
        {conversations.length > 0 && visibleConversations.length === 0 && (
          <EmptyState message={t("messages.noMatches", { query: query.trim() })} />
        )}
        {visibleConversations.map((conversation) => (
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
