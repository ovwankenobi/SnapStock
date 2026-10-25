import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { listSales } from "../../api/sales";
import AppLayout from "../../components/AppLayout";
import DateRangeFilter, { useDateRange } from "../../components/DateRangeFilter";
import EmptyState from "../../components/EmptyState";
import Icon from "../../components/Icon";
import IconButton from "../../components/IconButton";
import LoadingState from "../../components/LoadingState";
import { dayBoundsIso } from "../../lib/dates";
import { sellerNavItems } from "../../lib/nav";
import { useAuth } from "../auth/AuthContext";
import { formatShortTimestamp, paymentMethodLabel } from "./salesFormat";
import styles from "./sales.module.css";
import SaleStatusSheet from "./SaleStatusSheet";
import SalesHistoryRow from "./SalesHistoryRow";
import useDeleteSale from "./useDeleteSale";

const PAYMENT_METHODS = ["cash", "gcash", "maya", "bank_transfer", "other"];

// One row of filter chips; tapping the active chip again clears the filter back to All.
function ChipFilter({ id, label, allLabel, options, value, onChange }) {
  return (
    <div role="group" aria-labelledby={id}>
      <div id={id} className={styles["field-label"]}>
        {label}
      </div>
      <div className={styles.chips}>
        {[{ value: "", label: allLabel }, ...options].map((option) => {
          const active = option.value === value;
          return (
            <button
              key={option.value || "all"}
              type="button"
              aria-pressed={active}
              className={`${styles.chip} ${active ? styles["chip-active"] : ""}`}
              onClick={() => onChange(active ? "" : option.value)}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// Every receipt in the chosen period, newest first; tap one to open it (and void or refund it there).
// Deleting a completed sale from the list voids it, so it stays listed as Voided.
export default function TransactionsPage() {
  const navigate = useNavigate();
  const { t } = useAuth();
  const dateRange = useDateRange("today");
  const [saleType, setSaleType] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [saleToDelete, setSaleToDelete] = useState(null);
  const deleteMutation = useDeleteSale({ onSuccess: () => setSaleToDelete(null) });
  const { period } = dateRange;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["sales", period, saleType, paymentMethod],
    queryFn: () =>
      listSales({
        range: period.range,
        ...(period.range === "custom" ? dayBoundsIso(period.start, period.end) : {}),
        sale_type: saleType,
        paymentMethod,
        pageSize: 50,
      }),
    enabled: Boolean(period),
  });

  const sales = data?.items || [];
  const isFiltered = Boolean(saleType || paymentMethod);
  const typeLabel = { walk_in: t("transactions.walkIn"), itemized: t("transactions.account") }[saleType];
  // What's applied, shown on the collapsed Filters button.
  const filterSummary = [
    t(`dateRange.${dateRange.range}`),
    typeLabel,
    paymentMethod && paymentMethodLabel(paymentMethod),
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <AppLayout navItems={sellerNavItems()} title={t("nav.receipts")}>
      <div className={styles.analytics}>
        <div className={styles["analytics-side"]}>
          <button
            type="button"
            className={`${styles["filter-toggle"]} ${filtersOpen ? styles["filter-toggle-open"] : ""}`}
            aria-expanded={filtersOpen}
            aria-controls="receipts-filters"
            onClick={() => setFiltersOpen((open) => !open)}
          >
            <span className={styles["filter-toggle-label"]}>{t("transactions.filters")}</span>
            <span className={styles["filter-toggle-summary"]}>{filterSummary}</span>
            <span className={styles["filter-toggle-chevron"]} aria-hidden="true">
              <Icon name="chevron" size={16} />
            </span>
          </button>
          {filtersOpen && (
            <div id="receipts-filters" className={styles["filter-panel"]}>
              <DateRangeFilter state={dateRange} />
              <ChipFilter
                id="receipts-filter-type"
                label={t("transactions.filterType")}
                allLabel={t("transactions.all")}
                options={[
                  { value: "walk_in", label: t("transactions.walkIn") },
                  { value: "itemized", label: t("transactions.account") },
                ]}
                value={saleType}
                onChange={setSaleType}
              />
              <ChipFilter
                id="receipts-filter-payment"
                label={t("transactions.filterPayment")}
                allLabel={t("transactions.all")}
                options={PAYMENT_METHODS.map((value) => ({ value, label: paymentMethodLabel(value) }))}
                value={paymentMethod}
                onChange={setPaymentMethod}
              />
            </div>
          )}
        </div>
        <div className={styles["analytics-list"]}>
          {!period && <EmptyState message={t("dateRange.chooseValid")} />}
          {isLoading && <LoadingState message={t("analytics.loadingTransactions")} />}
          {isError && <EmptyState message={t("analytics.loadTransactionsError")} />}
          {data && sales.length === 0 && (
            <EmptyState message={t(isFiltered ? "transactions.noMatches" : "analytics.noSalesInRange")} />
          )}
          {data && data.total > sales.length && (
            <p className={styles.hint}>{t("analytics.showingLatest", { shown: sales.length, total: data.total })}</p>
          )}
          {sales.map((sale) => (
            <div key={sale.id} className={styles["history-row-with-action"]}>
              <SalesHistoryRow
                sale={{
                  saleType: sale.saleType,
                  status: sale.status,
                  paymentMethod: sale.paymentMethod,
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
