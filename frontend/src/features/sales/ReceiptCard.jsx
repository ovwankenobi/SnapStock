import { centsToPeso } from "../../lib/format";
import styles from "./sales.module.css";

export default function ReceiptCard({ receipt }) {
  return (
    <div className={styles["receipt-card"]}>
      <div className={styles["receipt-shop"]}>
        <div className={styles["receipt-shop-name"]}>{receipt.shopName}</div>
        <div className={styles["receipt-datetime"]}>{receipt.dateTimeLabel}</div>
      </div>
      <div className={styles["receipt-meta"]}>
        <div className={styles["receipt-meta-row"]}>
          <span>Receipt No.</span>
          <span>{receipt.code}</span>
        </div>
        <div className={styles["receipt-meta-row"]}>
          <span>Payment Method</span>
          <span>{receipt.paymentMethodLabel}</span>
        </div>
        {receipt.servedBy && (
          <div className={styles["receipt-meta-row"]}>
            <span>Served By</span>
            <span>{receipt.servedBy}</span>
          </div>
        )}
      </div>
      {receipt.buyerName && (
        <div className={styles["receipt-for"]}>
          <span>Receipt for</span>
          <span>{receipt.buyerName}</span>
        </div>
      )}
      {receipt.items && receipt.items.length > 0 ? (
        <div className={styles["receipt-items"]}>
          {receipt.items.map((item, i) => (
            <div key={i}>
              <div className={styles["receipt-item-row"]}>
                <span>{item.name}</span>
                <span>{centsToPeso(item.lineTotalCents)}</span>
              </div>
              <div className={styles["receipt-item-sub"]}>
                {item.qtyLabel} × {centsToPeso(item.unitPriceCents)}
                {item.priceUnitLabel ? `/${item.priceUnitLabel}` : ""}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className={styles["receipt-item-sub"]}>Walk-in Sale</div>
      )}
      <div className={styles["receipt-total-row"]}>
        <span className={styles["receipt-total-label"]}>Total</span>
        <span className={styles["receipt-total-value"]}>{centsToPeso(receipt.totalCents)}</span>
      </div>
    </div>
  );
}
