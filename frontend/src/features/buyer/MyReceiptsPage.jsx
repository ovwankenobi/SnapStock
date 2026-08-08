import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { getMyReceipts } from "../../api/catalog";
import AppLayout from "../../components/AppLayout";
import EmptyState from "../../components/EmptyState";
import LoadingState from "../../components/LoadingState";
import { formatShortTimestamp } from "../sales/salesFormat";
import SalesHistoryRow from "../sales/SalesHistoryRow";
import { buyerNavItems } from "../../lib/nav";
import styles from "./buyer.module.css";

export default function MyReceiptsPage() {
  const navigate = useNavigate();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["myReceipts"],
    queryFn: () => getMyReceipts({ pageSize: 50 }),
  });

  const receipts = data?.items || [];

  return (
    <AppLayout navItems={buyerNavItems()} title="My Receipts">
      <div className={styles["receipts-page"]}>
        {isLoading && <LoadingState message="Loading receipts…" />}
        {isError && <EmptyState message="Could not load your receipts." />}
        {!isLoading && !isError && receipts.length === 0 && (
          <EmptyState message="No purchases yet — receipts appear here after you buy something." />
        )}
        {receipts.map((receipt) => (
          <SalesHistoryRow
            key={receipt.id}
            sale={{
              saleType: receipt.saleType,
              title: receipt.sellerName,
              amountCents: receipt.totalCents,
              itemsSummary: `${receipt.itemCount} item${receipt.itemCount === 1 ? "" : "s"}`,
              timeLabel: formatShortTimestamp(receipt.createdAt),
            }}
            onClick={() => navigate(`/r/${receipt.receiptCode}`)}
          />
        ))}
      </div>
    </AppLayout>
  );
}
