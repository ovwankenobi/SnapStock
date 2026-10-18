import QuantityStepper from "../../components/QuantityStepper";
import { centsToPeso } from "../../lib/format";
import PriceEditor from "./PriceEditor";
import styles from "./sales.module.css";

export default function CartLineItem({ item, onIncrement, onDecrement, onQuantityClick, onPriceChange }) {
  return (
    <div className={styles["cart-item"]}>
      <div className={styles["cart-item-body"]}>
        <div className={styles["cart-item-name"]}>{item.name}</div>
        <PriceEditor
          productName={item.name}
          listPriceCents={item.listPriceCents}
          priceCents={item.unitPriceCents}
          costCents={item.costCents}
          unitLabel={item.priceUnitLabel}
          onChange={onPriceChange}
        />
      </div>
      {item.steppable ? (
        <QuantityStepper
          quantity={item.quantityLabel}
          onIncrement={onIncrement}
          onDecrement={onDecrement}
          onValueClick={onQuantityClick}
        />
      ) : (
        <button type="button" className={styles["cart-item-qty-button"]} onClick={onQuantityClick} aria-label="Enter quantity">
          {item.quantityLabel}
        </button>
      )}
      <div className={styles["cart-item-total"]}>{centsToPeso(item.lineTotalCents)}</div>
    </div>
  );
}
