import QuantityStepper from "../../components/QuantityStepper";
import { centsToPeso } from "../../lib/format";
import styles from "./sales.module.css";

export default function CartLineItem({ item, onIncrement, onDecrement }) {
  return (
    <div className={styles["cart-item"]}>
      <div className={styles["cart-item-body"]}>
        <div className={styles["cart-item-name"]}>{item.name}</div>
        <div className={styles["cart-item-price"]}>
          {centsToPeso(item.unitPriceCents)} / {item.priceUnitLabel}
        </div>
      </div>
      {item.steppable ? (
        <QuantityStepper quantity={item.quantityLabel} onIncrement={onIncrement} onDecrement={onDecrement} />
      ) : (
        <div className={styles["cart-item-price"]}>{item.quantityLabel}</div>
      )}
      <div className={styles["cart-item-total"]}>{centsToPeso(item.lineTotalCents)}</div>
    </div>
  );
}
