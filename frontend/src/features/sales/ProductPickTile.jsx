import ProductThumb from "../../components/ProductThumb";
import { centsToPeso, formatQuantity, lineTotalCents } from "../../lib/format";
import { saleUnitLabel } from "./salesFormat";
import styles from "./sales.module.css";

export default function ProductPickTile({ product, cartQuantity, onOpenAmount }) {
  const unit = saleUnitLabel(product.unitType, product.unitLabel);
  const selected = cartQuantity > 0;

  return (
    <div className={`${styles["pick-tile"]} ${selected ? styles["pick-tile-selected"] : ""}`}>
      <ProductThumb name={product.name} category={product.category} size="sm" />
      <div>
        <div className={styles["pick-tile-name"]}>{product.name}</div>
        <div className={styles["pick-tile-meta"]}>
          {centsToPeso(product.priceCents)}/{unit} · {formatQuantity(product.unitType, product.stockPieces)} {unit} left
        </div>
      </div>
      <button
        type="button"
        className={`${styles["pick-weigh-button"]} ${selected ? styles["pick-weigh-button-active"] : ""}`}
        onClick={onOpenAmount}
      >
        {selected
          ? `${formatQuantity(product.unitType, cartQuantity)} ${unit} · ${centsToPeso(
              lineTotalCents(product.priceCents, cartQuantity, product.unitType),
            )}`
          : "Tap to enter amount"}
      </button>
    </div>
  );
}
