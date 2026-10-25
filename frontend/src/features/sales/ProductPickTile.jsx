import ProductThumb from "../../components/ProductThumb";
import { centsToPeso, formatBundleStock, formatQuantity, isBundle, lineTotalCents, perPieceCents } from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import { saleLineUnit, saleUnitLabel } from "./salesFormat";
import styles from "./sales.module.css";

// `cartLines` are this product's cart entries: at most one bundle line and one by-piece line.
export default function ProductPickTile({ product, cartLines = [], onOpenAmount }) {
  const { t } = useAuth();
  const unit = saleUnitLabel(product.unitType, product.unitLabel);
  const bundle = isBundle(product.unitType);
  const selected = cartLines.length > 0;
  const stockText = bundle
    ? formatBundleStock(product.stockPieces, product.piecesPerUnit)
    : `${formatQuantity(product.unitType, product.stockPieces)} ${unit}`;

  const cartText = cartLines
    .map((line) => {
      const lineUnit = saleLineUnit(product, line.byPiece);
      return `${formatQuantity(lineUnit.unitType, line.quantity)} ${saleUnitLabel(lineUnit.unitType, lineUnit.unitLabel)}`;
    })
    .join(" + ");
  const cartTotal = cartLines.reduce((sum, line) => {
    const lineUnit = saleLineUnit(product, line.byPiece);
    return sum + lineTotalCents(line.unitPriceCents ?? lineUnit.priceCents, line.quantity, lineUnit.unitType);
  }, 0);

  return (
    <div className={`${styles["pick-tile"]} ${selected ? styles["pick-tile-selected"] : ""}`}>
      <ProductThumb name={product.name} category={product.category} size="sm" />
      <div>
        <div className={styles["pick-tile-name"]}>{product.name}</div>
        <div className={styles["pick-tile-meta"]}>
          {centsToPeso(product.priceCents)}/{unit} · {stockText} left
        </div>
        {bundle && (
          <div className={styles["pick-tile-note"]}>
            {t("checkout.alsoPerPiece", {
              price: centsToPeso(perPieceCents(product.priceCents, product.piecesPerUnit)),
            })}
          </div>
        )}
      </div>
      <button
        type="button"
        className={`${styles["pick-weigh-button"]} ${selected ? styles["pick-weigh-button-active"] : ""}`}
        onClick={onOpenAmount}
      >
        {selected ? `${cartText} · ${centsToPeso(cartTotal)}` : "Tap to enter amount"}
      </button>
    </div>
  );
}
