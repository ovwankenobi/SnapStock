import { useNavigate } from "react-router-dom";

import Badge from "../../components/Badge";
import styles from "../../components/chat.module.css";
import { centsToPeso, mediaUrl } from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import { SALE_STATUS_TAG } from "../sales/salesFormat";

// The chat card posted when a buyer's online order is ready to approve. The seller's card opens the
// order under New Sale → Buyer Account; the buyer's opens their order page.
export default function OrderCardBubble({ order, align }) {
  const navigate = useNavigate();
  const { user, t } = useAuth();
  const isSeller = user?.role === "seller";
  const isPending = order.status === "pending_payment";
  const statusTag =
    order.status === "completed"
      ? { tone: "success", label: t("messages.orderCard.approved") }
      : SALE_STATUS_TAG[order.status];

  function open() {
    if (!isSeller) navigate(`/buyer/orders/${order.id}`);
    else navigate(isPending ? `/sales?path=account&order=${order.id}` : `/sales/${order.id}/receipt`);
  }

  return (
    <div className={`${styles["bubble-row"]} ${styles[`bubble-row-${align}`]}`}>
      <button type="button" className={styles["order-card"]} onClick={open}>
        <div className={styles["order-card-top"]}>
          <span className={styles["order-card-label"]}>{t("messages.orderCard.label")}</span>
          {statusTag && <Badge tone={statusTag.tone}>{statusTag.label}</Badge>}
        </div>
        <div className={styles["order-card-text"]}>
          {t("messages.orderCard.bought", { name: order.buyerName, items: order.itemsSummary })}
        </div>
        <div className={styles["order-card-total"]}>{centsToPeso(order.totalCents)}</div>
        {order.paymentProofUrl && (
          <img className={styles["order-card-proof"]} src={mediaUrl(order.paymentProofUrl)} alt={t("orders.proofTitle")} />
        )}
        {isPending && (
          <div className={styles["order-card-question"]}>
            {order.paymentMethod === "cash" ? t("messages.orderCard.cashQuestion") : t("messages.orderCard.proofQuestion")}
          </div>
        )}
        <span className={styles["order-card-action"]}>
          {isSeller && isPending ? t("messages.orderCard.review") : t("messages.orderCard.view")}
        </span>
      </button>
    </div>
  );
}
