import { useSearchParams } from "react-router-dom";

import AppLayout from "../../components/AppLayout";
import DateRangeFilter, { useDateRange } from "../../components/DateRangeFilter";
import EmptyState from "../../components/EmptyState";
import SegmentedControl from "../../components/SegmentedControl";
import { sellerNavItems } from "../../lib/nav";
import { useAuth } from "../auth/AuthContext";
import styles from "./analytics.module.css";
import ForecastTab from "./ForecastTab";
import InsightsFeed from "./InsightsFeed";
import ProfitTab from "./ProfitTab";
import SalesTab from "./SalesTab";
import StockTab from "./StockTab";

const TABS = ["sales", "profit", "stock", "forecast"];
// Sales and Profit cover a chosen period; Stock and Forecast always look at current stock and recent demand.
const DATED_TABS = new Set(["sales", "profit"]);

export default function AnalyticsPage() {
  const { t } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = TABS.includes(searchParams.get("tab")) ? searchParams.get("tab") : "sales";
  const dateRange = useDateRange("week");

  return (
    <AppLayout navItems={sellerNavItems()} title={t("nav.analytics")}>
      <div className={styles.page}>
        <InsightsFeed />

        <SegmentedControl
          options={TABS.map((value) => ({ value, label: t(`analytics.tabs.${value}`) }))}
          value={tab}
          onChange={(value) => setSearchParams({ tab: value }, { replace: true })}
        />

        {DATED_TABS.has(tab) && <DateRangeFilter state={dateRange} />}
        {DATED_TABS.has(tab) && !dateRange.period && <EmptyState message={t("dateRange.chooseValid")} />}

        {tab === "sales" && dateRange.period && <SalesTab period={dateRange.period} />}
        {tab === "profit" && dateRange.period && <ProfitTab period={dateRange.period} />}
        {tab === "stock" && <StockTab />}
        {tab === "forecast" && <ForecastTab />}
      </div>
    </AppLayout>
  );
}
