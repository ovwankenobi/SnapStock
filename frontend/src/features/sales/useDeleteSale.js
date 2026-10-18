import { useMutation, useQueryClient } from "@tanstack/react-query";

import { voidSale } from "../../api/sales";

// Deleting a transaction voids it: its stock comes back and it drops out of every report,
// but the record (and its receipt) stays, marked Voided.
export default function useDeleteSale({ onSuccess } = {}) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ saleId, reason }) => voidSale(saleId, reason),
    onSuccess: (updated) => {
      queryClient.setQueryData(["sale", updated.id], updated);
      for (const key of ["sales", "products", "lowStockProducts", "pendingOrders"]) {
        queryClient.invalidateQueries({ queryKey: [key] });
      }
      queryClient.invalidateQueries({ predicate: (query) => String(query.queryKey[0]).startsWith("analytics") });
      onSuccess?.(updated);
    },
  });
}
