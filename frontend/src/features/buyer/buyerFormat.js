import { unitSuffix } from "../../lib/format";

const STOCK_BADGE = {
  in_stock: { tone: "success", label: "In Stock" },
  low: { tone: "warning", label: "Low Stock" },
  out: { tone: "danger", label: "Out of Stock" },
};

export function stockBadge(stockStatus) {
  return STOCK_BADGE[stockStatus] || { tone: "neutral", label: stockStatus };
}

// Adapts a CatalogProductRead into the shape ProductFeedCard expects.
export function toFeedListing(product) {
  const badge = stockBadge(product.stockStatus);
  return {
    id: product.id,
    sellerId: product.sellerId,
    sellerName: product.sellerName,
    productName: product.name,
    photoUrl: product.photoUrl,
    category: product.category,
    priceCents: product.priceCents,
    unitLabel: unitSuffix(product.unitType),
    badgeTone: badge.tone,
    badgeLabel: badge.label,
  };
}
