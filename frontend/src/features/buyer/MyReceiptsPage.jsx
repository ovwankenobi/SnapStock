import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { getMyReceipts } from "../../api/catalog";
import AppLayout from "../../components/AppLayout";
import EmptyState from "../../components/EmptyState";
import LoadingState from "../../components/LoadingState";
import { formatShortTimestamp } from "../sales/salesFormat";
import SalesHistoryRow from "../sales/SalesHistoryRow";
import { buyerNavItems } from "../../lib/nav";
import { useAuth } from "../auth/AuthContext";
import styles from "./buyer.module.css";

// Orders that never became a paid sale open the order page instead of the receipt.
const ORDER_STATUSES = new Set(["pending_payment", "cancelled"]);

export default function MyReceiptsPage() {
  const navigate = useNavigate();
  const { t } = useAuth();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["myReceipts"],
    queryFn: () => getMyReceipts({ pageSize: 50 }),
  });

  const receipts = data?.items || [];

  return (
    <AppLayout navItems={buyerNavItems()} title={t("buyerTransactions.title")}>
      <div className={styles["receipts-page"]}>
        {isLoading && <LoadingState message={t("buyerTransactions.loading")} />}
        {isError && <EmptyState message={t("buyerTransactions.loadError")} />}
        {!isLoading && !isError && receipts.length === 0 && (
          <EmptyState message={t("buyerTransactions.empty")} />
        )}
        {receipts.map((receipt) => (
          <SalesHistoryRow
            key={receipt.id}
            sale={{
              saleType: receipt.saleType,
              status: receipt.status,
              title: receipt.sellerName,
              amountCents: receipt.totalCents,
              itemsSummary: `${receipt.itemCount} item${receipt.itemCount === 1 ? "" : "s"}`,
              timeLabel: formatShortTimestamp(receipt.createdAt),
            }}
            showTag={false}
            onClick={() =>
              navigate(ORDER_STATUSES.has(receipt.status) ? `/buyer/orders/${receipt.id}` : `/r/${receipt.receiptCode}`)
            }
          />
        ))}
      </div>
    </AppLayout>
  );
}
