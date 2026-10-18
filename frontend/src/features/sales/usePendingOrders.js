import { useQuery } from "@tanstack/react-query";

import { listSales } from "../../api/sales";

// Buyer orders waiting for the seller to approve. Shared by the Sell nav badge, the dashboard banner
// and New Sale → Buyer Account.
export function usePendingOrders({ enabled = true } = {}) {
  return useQuery({
    queryKey: ["pendingOrders"],
    queryFn: () => listSales({ status: "pending_payment", pageSize: 100 }),
    refetchInterval: 15000,
    enabled,
  });
}
