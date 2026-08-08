import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getSalesTrend, getSummary, getTopProducts } from "../../api/analytics";
import { getLowStockProducts } from "../../api/products";
import AppLayout from "../../components/AppLayout";
import EmptyState from "../../components/EmptyState";
import LoadingState from "../../components/LoadingState";
import StatTile from "../../components/StatTile";
import { centsToPeso } from "../../lib/format";
import { sellerNavItems } from "../../lib/nav";
import { useAuth } from "../auth/AuthContext";
import LowStockAlert from "./LowStockAlert";
import LowStockBanner from "./LowStockBanner";
import PinnableCard from "./PinnableCard";
import QuickActionTile from "./QuickActionTile";
import SalesTrendChart from "./SalesTrendChart";
import styles from "./dashboard.module.css";
import { usePinnedCards } from "./usePinnedCards";

const CARD_IDS = ["todaySales", "todayRevenue", "lowStock", "topSeller"];

const TODAY_LABEL = new Intl.DateTimeFormat(undefined, { dateStyle: "long" }).format(new Date());

export default function SellerDashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { pinnedIds, togglePinned, isCustomizing, setIsCustomizing } = usePinnedCards(CARD_IDS);

  const { data: summary, isLoading: isLoadingSummary, isError: isSummaryError } = useQuery({
    queryKey: ["analyticsSummary"],
    queryFn: getSummary,
  });
  const { data: lowStock } = useQuery({ queryKey: ["lowStockProducts"], queryFn: getLowStockProducts });
  const { data: topProducts } = useQuery({
    queryKey: ["analyticsTopProducts", "today"],
    queryFn: () => getTopProducts({ range: "today", limit: 1 }),
  });
  const { data: trend } = useQuery({
    queryKey: ["analyticsSalesTrend", "week"],
    queryFn: () => getSalesTrend({ range: "week" }),
  });

  const isInitialLoading = isLoadingSummary && !summary;

  const topSeller = topProducts?.[0];
  const changePct = summary?.weekOverWeekRevenueChangePct;

  const cardsById = {
    todaySales: {
      node: <StatTile label="Today's Sales" value={summary ? String(summary.todaySaleCount) : "—"} />,
    },
    todayRevenue: {
      node: (
        <StatTile
          label="Today's Revenue"
          value={summary ? centsToPeso(summary.todayRevenueCents) : "—"}
          subLabel={
            changePct != null ? `${changePct > 0 ? "+" : ""}${changePct}% vs last week` : "vs last week: —"
          }
        />
      ),
    },
    lowStock: {
      node: (
        <LowStockAlert
          count={lowStock?.length || 0}
          productNames={(lowStock || []).map((product) => product.name)}
          onClick={() => navigate("/inventory")}
        />
      ),
    },
    topSeller: {
      node: (
        <StatTile
          label="Top Seller"
          value={topSeller ? topSeller.productName : "No sales yet"}
          subLabel={topSeller ? `${topSeller.quantitySold} sold today` : undefined}
        />
      ),
    },
  };

  const pinned = pinnedIds.filter((id) => cardsById[id]);
  const unpinned = CARD_IDS.filter((id) => !pinnedIds.includes(id));

  return (
    <AppLayout
      navItems={sellerNavItems()}
      title="Home"
      brandLabel={user?.sellerProfile?.businessName}
      headerAction={
        <button type="button" className={styles["customize-button"]} onClick={() => setIsCustomizing((v) => !v)}>
          {isCustomizing ? "Done" : "Customize"}
        </button>
      }
    >
      <div className={styles.page}>
        <div className={styles.date}>{TODAY_LABEL}</div>
        <LowStockBanner />

        {isInitialLoading && <LoadingState message="Loading your dashboard…" />}
        {isSummaryError && <EmptyState message="Could not load today's stats." />}

        <div className={styles.stats}>
          {pinned.map((id) => (
            <PinnableCard
              key={id}
              pinned
              isCustomizing={isCustomizing}
              onToggle={() => togglePinned(id)}
            >
              {cardsById[id].node}
            </PinnableCard>
          ))}
        </div>

        {isCustomizing && unpinned.length > 0 && (
          <>
            <div className={styles["more-stats-label"]}>More stats — tap to pin to the top</div>
            <div className={styles["more-stats"]}>
              {unpinned.map((id) => (
                <PinnableCard key={id} pinned={false} isCustomizing onToggle={() => togglePinned(id)}>
                  {cardsById[id].node}
                </PinnableCard>
              ))}
            </div>
          </>
        )}

        <SalesTrendChart points={trend} />

        <div className={styles["section-label"]}>Quick Actions</div>
        <div className={styles["quick-actions"]}>
          <QuickActionTile to="/inventory" icon="box" label="Inventory" />
          <QuickActionTile to="/analytics" icon="chart" label="Sales History" />
          <QuickActionTile to="/messages" icon="chat" label="Messages" />
          <QuickActionTile to="/sales" icon="plus" label="New Sale" />
          <QuickActionTile to="/profile" icon="user" label="Profile" />
        </div>
      </div>
    </AppLayout>
  );
}
