import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { buyProduct, getCatalogProduct } from "../../api/catalog";
import { listConversations, listMessages, markConversationRead, sendMessage } from "../../api/messages";
import AppLayout from "../../components/AppLayout";
import ChatBubble from "../../components/ChatBubble";
import chatStyles from "../../components/chat.module.css";
import ChatComposer from "../../components/ChatComposer";
import EmptyState from "../../components/EmptyState";
import ProductThumb from "../../components/ProductThumb";
import { centsToPeso } from "../../lib/format";
import { buyerNavItems, sellerNavItems } from "../../lib/nav";
import { useAuth } from "../auth/AuthContext";
import BuySheet from "../buyer/BuySheet";
import styles from "./messages.module.css";
import OrderCardBubble from "./OrderCardBubble";

export default function ChatPage() {
  const { conversationId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const [showBuySheet, setShowBuySheet] = useState(false);
  const [buyError, setBuyError] = useState("");

  const { data: conversationsData } = useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
    refetchInterval: 8000,
  });
  const conversation = conversationsData?.items?.find((c) => c.id === conversationId);
  const pinnedProductId = conversation?.product?.id;
  const canBuy = user?.role === "buyer" && Boolean(pinnedProductId);

  // BuySheet needs unit/stock fields the conversation's product summary doesn't carry.
  const { data: catalogProduct } = useQuery({
    queryKey: ["catalogProduct", pinnedProductId],
    queryFn: () => getCatalogProduct(pinnedProductId),
    enabled: canBuy,
  });

  const buyMutation = useMutation({
    mutationFn: (payload) => buyProduct(pinnedProductId, payload),
    onSuccess: (sale) => {
      navigate(`/buyer/orders/${sale.id}`);
    },
    onError: (err) => {
      setBuyError(err.response?.data?.detail || "Could not place the order.");
    },
  });

  const {
    data: messagesData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["messages", conversationId],
    queryFn: () => listMessages(conversationId),
    refetchInterval: 6000,
  });
  const messages = [...(messagesData?.items || [])].reverse();

  useEffect(() => {
    if (!conversationId) return;
    markConversationRead(conversationId).then(() => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId, messagesData?.items?.length]);

  const sendMutation = useMutation({
    mutationFn: (body) => sendMessage(conversationId, body),
    onSuccess: () => {
      setDraft("");
      queryClient.invalidateQueries({ queryKey: ["messages", conversationId] });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  const navItems = user?.role === "seller" ? sellerNavItems() : buyerNavItems();

  return (
    <AppLayout
      navItems={navItems}
      title={conversation?.otherUser?.fullName || "Conversation"}
      backTo="/messages"
      hideBottomNav
    >
      <div className={styles["chat-page"]}>
        {conversation?.product && (
          <div className={styles["product-pin"]}>
            <ProductThumb
              name={conversation.product.name}
              photoUrl={conversation.product.photoUrl}
              size="sm"
            />
            <div className={styles["product-pin-body"]}>
              <div className={styles["product-pin-name"]}>{conversation.product.name}</div>
              <div className={styles["product-pin-price"]}>{centsToPeso(conversation.product.priceCents)}</div>
            </div>
            {canBuy && catalogProduct && (
              <button
                type="button"
                className={styles["product-pin-buy"]}
                disabled={catalogProduct.stockStatus === "out"}
                onClick={() => {
                  setBuyError("");
                  setShowBuySheet(true);
                }}
              >
                {catalogProduct.stockStatus === "out" ? "Out of Stock" : "Buy"}
              </button>
            )}
          </div>
        )}

        {isError && <EmptyState message="Could not load this conversation." />}
        {!isError && (
          <div className={chatStyles.thread}>
            {isLoading && <p className={styles.hint}>Loading messages...</p>}
            {!isLoading && messages.length === 0 && (
              <EmptyState message="No messages yet — say hello!" />
            )}
            {messages.map((message) => {
              const align = message.senderId === user?.id ? "end" : "start";
              return message.order ? (
                <OrderCardBubble key={message.id} order={message.order} align={align} />
              ) : (
                <ChatBubble key={message.id} text={message.body} align={align} />
              );
            })}
          </div>
        )}

        <ChatComposer
          value={draft}
          onChange={setDraft}
          onSend={() => sendMutation.mutate(draft)}
        />
      </div>

      {showBuySheet && catalogProduct && (
        <BuySheet
          product={catalogProduct}
          isSubmitting={buyMutation.isPending}
          error={buyError}
          onClose={() => setShowBuySheet(false)}
          onConfirm={(payload) => buyMutation.mutate(payload)}
        />
      )}
    </AppLayout>
  );
}
