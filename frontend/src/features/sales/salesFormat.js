import { formatQuantity, isMeasured, perPieceCents, unitSuffix } from "../../lib/format";

// How a product is priced and counted on one sale line. A bundle sold `byPiece` becomes a
// piece line at the bundle price / pieces per bundle (mirrors backend build_sale_item).
export function saleLineUnit(product, byPiece = false) {
  if (byPiece) {
    return {
      unitType: "piece",
      unitLabel: null,
      priceCents: perPieceCents(product.priceCents, product.piecesPerUnit),
      costCents: perPieceCents(product.costCents, product.piecesPerUnit),
    };
  }
  return {
    unitType: product.unitType,
    unitLabel: product.unitLabel,
    priceCents: product.priceCents,
    costCents: product.costCents,
  };
}

const PAYMENT_LABELS = {
  cash: "Cash",
  gcash: "GCash",
  maya: "Maya",
  bank_transfer: "Bank Transfer",
  other: "Other",
};

export function paymentMethodLabel(value) {
  return PAYMENT_LABELS[value] || value;
}

export function saleUnitLabel(unitType, unitLabel) {
  return unitSuffix(unitType, unitLabel);
}

export function saleQuantityLabel(unitType, quantity, unitLabel) {
  return isMeasured(unitType)
    ? `${formatQuantity(unitType, quantity)} ${unitSuffix(unitType, unitLabel)}`
    : String(quantity);
}

export function formatReceiptTimestamp(isoString) {
  if (!isoString) return "";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(isoString));
}

export function formatShortTimestamp(isoString) {
  if (!isoString) return "";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(isoString));
}

function mapReceiptItems(items) {
  return (items || []).map((item) => ({
    name: item.productNameSnapshot ?? item.name,
    qtyLabel: saleQuantityLabel(
      item.unitTypeSnapshot ?? item.unitType,
      item.quantity,
      item.unitLabelSnapshot ?? item.unitLabel,
    ),
    unitPriceCents: item.unitPriceCentsSnapshot ?? item.unitPriceCents,
    // Only the seller's own SaleRead carries the list price; the public receipt shows the charged price.
    listPriceCents: item.listPriceCentsSnapshot ?? null,
    priceUnitLabel: saleUnitLabel(item.unitTypeSnapshot ?? item.unitType, item.unitLabelSnapshot ?? item.unitLabel),
    lineTotalCents: item.lineTotalCents,
  }));
}

// Adapts a seller-authenticated SaleRead into the shape ReceiptCard expects.
export function saleToReceipt(sale, { shopName, servedBy } = {}) {
  return {
    shopName,
    dateTimeLabel: formatReceiptTimestamp(sale.createdAt),
    code: sale.receiptCode,
    paymentMethodLabel: paymentMethodLabel(sale.paymentMethod),
    servedBy,
    buyerName: sale.buyerName,
    items: mapReceiptItems(sale.items),
    subtotalCents: sale.subtotalCents,
    discountCents: sale.discountCents || 0,
    totalCents: sale.totalCents,
    status: sale.status,
  };
}

// Adapts the trimmed public PublicReceipt payload into the same shape.
export function publicReceiptToReceipt(receipt) {
  return {
    shopName: receipt.businessName,
    dateTimeLabel: formatReceiptTimestamp(receipt.createdAt),
    code: receipt.receiptCode,
    paymentMethodLabel: paymentMethodLabel(receipt.paymentMethod),
    servedBy: null,
    buyerName: null,
    items: mapReceiptItems(receipt.items),
    subtotalCents: receipt.subtotalCents,
    discountCents: receipt.discountCents || 0,
    totalCents: receipt.totalCents,
    status: receipt.status,
  };
}

// Badge for every status other than a plain completed sale.
export const SALE_STATUS_TAG = {
  voided: { tone: "danger", label: "Voided" },
  refunded: { tone: "warning", label: "Refunded" },
  pending_payment: { tone: "info", label: "Awaiting payment" },
  cancelled: { tone: "danger", label: "Cancelled" },
};
