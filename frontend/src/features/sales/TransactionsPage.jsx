import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { listSales } from "../../api/sales";
import AppLayout from "../../components/AppLayout";
import DateRangeFilter, { useDateRange } from "../../components/DateRangeFilter";
import EmptyState from "../../components/EmptyState";
import IconButton from "../../components/IconButton";
import LoadingState from "../../components/LoadingState";
import { dayBoundsIso } from "../../lib/dates";
import { sellerNavItems } from "../../lib/nav";
import { useAuth } from "../auth/AuthContext";
import { formatShortTimestamp } from "./salesFormat";
import styles from "./sales.module.css";
import SaleStatusSheet from "./SaleStatusSheet";
import SalesHistoryRow from "./SalesHistoryRow";
import useDeleteSale from "./useDeleteSale";

// Every receipt in the chosen period, newest first; tap one to open it (and void or refund it there).
// Deleting a completed sale from the list voids it, so it stays listed as Voided.
export default function TransactionsPage() {
  const navigate = useNavigate();
  const { t } = useAuth();
  const dateRange = useDateRange("today");
  const [saleToDelete, setSaleToDelete] = useState(null);
  const deleteMutation = useDeleteSale({ onSuccess: () => setSaleToDelete(null) });
  const { period } = dateRange;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["sales", period],
    queryFn: () =>
      listSales({
        range: period.range,
        ...(period.range === "custom" ? dayBoundsIso(period.start, period.end) : {}),
        pageSize: 50,
      }),
    enabled: Boolean(period),
  });

  const sales = data?.items || [];

  return (
    <AppLayout navItems={sellerNavItems()} title={t("nav.receipts")}>
      <div className={styles.analytics}>
        <div className={styles["analytics-side"]}>
          <DateRangeFilter state={dateRange} />
        </div>
        <div className={styles["analytics-list"]}>
          {!period && <EmptyState message={t("dateRange.chooseValid")} />}
          {isLoading && <LoadingState message={t("analytics.loadingTransactions")} />}
          {isError && <EmptyState message={t("analytics.loadTransactionsError")} />}
          {data && sales.length === 0 && <EmptyState message={t("analytics.noSalesInRange")} />}
          {data && data.total > sales.length && (
            <p className={styles.hint}>{t("analytics.showingLatest", { shown: sales.length, total: data.total })}</p>
          )}
          {sales.map((sale) => (
            <div key={sale.id} className={styles["history-row-with-action"]}>
              <SalesHistoryRow
                sale={{
                  saleType: sale.saleType,
                  status: sale.status,
                  title: sale.saleType === "itemized" ? sale.buyerName || "Buyer" : "Walk-in",
                  amountCents: sale.totalCents,
                  itemsSummary:
                    sale.itemCount > 0 ? `${sale.itemCount} item${sale.itemCount === 1 ? "" : "s"}` : sale.note,
                  timeLabel: formatShortTimestamp(sale.createdAt),
                }}
                onClick={() => navigate(`/sales/${sale.id}/receipt`)}
              />
              {sale.status === "completed" && (
                <IconButton icon="trash" variant="danger" label={t("saleStatus.delete.label")} onClick={() => setSaleToDelete(sale)} />
              )}
            </div>
          ))}
        </div>
      </div>
      {saleToDelete && (
        <SaleStatusSheet
          action="delete"
          sale={saleToDelete}
          isSubmitting={deleteMutation.isPending}
          error={deleteMutation.error?.response?.data?.detail || (deleteMutation.isError ? t("saleStatus.error") : "")}
          onConfirm={(reason) => deleteMutation.mutate({ saleId: saleToDelete.id, reason })}
          onClose={() => {
            deleteMutation.reset();
            setSaleToDelete(null);
          }}
        />
      )}
    </AppLayout>
  );
}
