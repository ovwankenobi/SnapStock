import ProductThumb from "../../components/ProductThumb";
import { centsToPeso } from "../../lib/format";
import { saleUnitLabel } from "./salesFormat";
import styles from "./sales.module.css";

export default function ProductPickTile({ product, cartQuantity, onQuantityChange, onOpenWeigh }) {
  const isWeighed = product.unitType === "grams";
  const unit = saleUnitLabel(product.unitType);
  const selected = cartQuantity > 0;

  return (
    <div className={`${styles["pick-tile"]} ${selected ? styles["pick-tile-selected"] : ""}`}>
      <ProductThumb name={product.name} category={product.category} size="sm" />
      <div>
        <div className={styles["pick-tile-name"]}>{product.name}</div>
        <div className={styles["pick-tile-meta"]}>
          {centsToPeso(product.priceCents)}/{unit} · {product.stockPieces} {unit} left
        </div>
      </div>
      {isWeighed ? (
        <button
          type="button"
          className={`${styles["pick-weigh-button"]} ${selected ? styles["pick-weigh-button-active"] : ""}`}
          onClick={onOpenWeigh}
        >
          {selected ? `${cartQuantity}g · ${centsToPeso(product.priceCents * cartQuantity)}` : "Tap to enter weight"}
        </button>
      ) : (
        <div className={styles["pick-qty-row"]}>
          <input
            className={styles["pick-qty-input"]}
            inputMode="numeric"
            placeholder="0"
            value={cartQuantity || ""}
            onChange={(e) => onQuantityChange(e.target.value.replace(/[^0-9]/g, ""))}
          />
          <div className={styles["pick-qty-suffix"]}>{unit}</div>
        </div>
      )}
    </div>
  );
}
