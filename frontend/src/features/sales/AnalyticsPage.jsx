import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { getForecast } from "../../api/analytics";
import { listSales } from "../../api/sales";
import AppLayout from "../../components/AppLayout";
import EmptyState from "../../components/EmptyState";
import LoadingState from "../../components/LoadingState";
import SegmentedControl from "../../components/SegmentedControl";
import { sellerNavItems } from "../../lib/nav";
import DemandForecastList from "./DemandForecastList";
import { formatShortTimestamp } from "./salesFormat";
import styles from "./sales.module.css";
import SalesHistoryRow from "./SalesHistoryRow";

const FILTER_OPTIONS = [
  { value: "today", label: "Today" },
  { value: "week", label: "This Week" },
  { value: "month", label: "This Month" },
];

export default function AnalyticsPage() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState("today");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["sales", { range: filter }],
    queryFn: () => listSales({ range: filter, pageSize: 50 }),
  });

  const {
    data: forecasts,
    isLoading: isLoadingForecast,
    isError: isForecastError,
  } = useQuery({ queryKey: ["analyticsForecast"], queryFn: getForecast });

  const sales = data?.items || [];

  return (
    <AppLayout navItems={sellerNavItems()} title="Sales History">
      <div className={styles.analytics}>
        <div className={styles["analytics-side"]}>
          <SegmentedControl options={FILTER_OPTIONS} value={filter} onChange={setFilter} />
          {isLoadingForecast && <LoadingState message="Loading forecast…" />}
          {isForecastError && <EmptyState message="Could not load the demand forecast." />}
          {!isLoadingForecast && !isForecastError && <DemandForecastList forecasts={forecasts} />}
        </div>
        <div className={styles["analytics-list"]}>
          {isLoading && <LoadingState message="Loading sales history…" />}
          {isError && <EmptyState message="Could not load sales history." />}
          {!isLoading && !isError && sales.length === 0 && <EmptyState message="No sales in this range yet." />}
          {sales.map((sale) => (
            <SalesHistoryRow
              key={sale.id}
              sale={{
                saleType: sale.saleType,
                title: sale.saleType === "itemized" ? sale.buyerName || "Buyer" : "Walk-in",
                amountCents: sale.totalCents,
                itemsSummary:
                  sale.itemCount > 0 ? `${sale.itemCount} item${sale.itemCount === 1 ? "" : "s"}` : sale.note,
                timeLabel: formatShortTimestamp(sale.createdAt),
              }}
              onClick={() => navigate(`/sales/${sale.id}/receipt`)}
            />
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
