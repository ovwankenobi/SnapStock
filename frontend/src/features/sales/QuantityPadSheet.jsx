import { centsToPeso, formatQuantity, isMeasured, lineTotalCents, parseQuantityInput, unitSuffix } from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import AmountPadSheet from "./AmountPadSheet";
import styles from "./sales.module.css";

// In whole units of the product's measure (kg, yd, m, ...).
const MEASURE_PRESETS = ["0.25", "0.5", "1"];

// Keypad quantity entry for one product. `currentQuantity` is the stored quantity already in the cart
// (0 = not in the cart yet); confirming 0 on an item in the cart removes it.
export default function QuantityPadSheet({ product, currentQuantity = 0, onConfirm, onClose }) {
  const { t } = useAuth();
  const measured = isMeasured(product.unitType);
  const unit = unitSuffix(product.unitType, product.unitLabel);
  const inCart = currentQuantity > 0;

  return (
    <AmountPadSheet
      title={product.name}
      subtitle={`${centsToPeso(product.priceCents)}/${unit} · ${formatQuantity(product.unitType, product.stockPieces)} ${unit} left`}
      initialValue={inCart ? formatQuantity(product.unitType, currentQuantity) : ""}
      maxDecimals={measured ? 3 : 0}
      suffix={unit}
      presets={measured ? MEASURE_PRESETS.map((value) => ({ value, label: `${value} ${unit}` })) : []}
      renderFooter={(value) => (
        <div className={styles["dialog-total-row"]}>
          <div className={styles["dialog-total-label"]}>{t("checkout.subtotal")}</div>
          <div className={styles["dialog-total-value"]}>
            {centsToPeso(lineTotalCents(product.priceCents, parseQuantityInput(value, product.unitType), product.unitType))}
          </div>
        </div>
      )}
      canConfirm={(value) => inCart || parseQuantityInput(value, product.unitType) > 0}
      confirmLabel={(value) => {
        if (!inCart) return t("checkout.addToCart");
        return parseQuantityInput(value, product.unitType) > 0 ? t("checkout.updateCart") : t("checkout.removeFromCart");
      }}
      onConfirm={(value) => onConfirm(parseQuantityInput(value, product.unitType))}
      onClose={onClose}
    />
  );
}
