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

const SALE_UNIT_LABELS = { piece: "pc", bundle: "bundle", grams: "g" };

export function saleUnitLabel(unitType) {
  return SALE_UNIT_LABELS[unitType] || unitType;
}

export function saleQuantityLabel(unitType, quantity) {
  return unitType === "grams" ? `${quantity} g` : String(quantity);
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
    qtyLabel: saleQuantityLabel(item.unitTypeSnapshot ?? item.unitType, item.quantity),
    unitPriceCents: item.unitPriceCentsSnapshot ?? item.unitPriceCents,
    priceUnitLabel: saleUnitLabel(item.unitTypeSnapshot ?? item.unitType),
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
    totalCents: sale.totalCents,
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
    totalCents: receipt.totalCents,
  };
}
