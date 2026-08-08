import { Link } from "react-router-dom";

import Badge from "../../components/Badge";
import ProductThumb from "../../components/ProductThumb";
import { centsToPeso, mediaUrl, unitSuffix } from "../../lib/format";
import styles from "./inventory.module.css";

const STOCK_BADGE = {
  in_stock: { tone: "success", label: "In Stock" },
  low: { tone: "warning", label: "Low Stock" },
  out: { tone: "danger", label: "Out of Stock" },
};

export default function ProductListItem({ product, onQuickSell }) {
  const unit = unitSuffix(product.unitType);
  const badge = STOCK_BADGE[product.stockStatus];

  return (
    <div className={styles.item}>
      <Link to={`/inventory/${product.id}/edit`} className={styles["item-link"]}>
        <ProductThumb name={product.name} category={product.category} photoUrl={mediaUrl(product.photoUrl)} />
        <div className={styles["item-body"]}>
          <div className={styles["item-name"]}>{product.name}</div>
          <div className={styles["item-meta"]}>
            <span className={styles["item-price"]}>
              {centsToPeso(product.priceCents)}/{unit}
            </span>
            <span className={styles["item-stock"]}>
              · {product.stockPieces} {unit}
            </span>
          </div>
          <div className={styles["item-badge"]}>
            <Badge tone={badge.tone}>{badge.label}</Badge>
          </div>
        </div>
      </Link>
      <button
        type="button"
        className={styles["quick-sell"]}
        disabled={product.stockStatus === "out"}
        onClick={() => onQuickSell(product)}
        aria-label={`Quick sell ${product.name}`}
      >
        −1
      </button>
    </div>
  );
}
