import { useState } from "react";

import SegmentedControl from "../../components/SegmentedControl";
import {
  centsToPeso,
  formatBundleStock,
  formatQuantity,
  isBundle,
  isMeasured,
  lineTotalCents,
  parseQuantityInput,
  unitSuffix,
} from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import AmountPadSheet from "./AmountPadSheet";
import { saleLineUnit } from "./salesFormat";
import styles from "./sales.module.css";

// In whole units of the product's measure (kg, yd, m, ...).
const MEASURE_PRESETS = ["0.25", "0.5", "1"];

// Keypad quantity entry for one product. `quantityFor(byPiece)` is the stored quantity already in
// the cart for that line (0 = not in the cart yet); confirming 0 on a line in the cart removes it.
// Bundle products get a Bundle / Per piece toggle; `onConfirm(quantity, byPiece)`.
export default function QuantityPadSheet({ product, quantityFor, initialByPiece = false, onConfirm, onClose }) {
  const { t } = useAuth();
  const bundle = isBundle(product.unitType);
  const [byPiece, setByPiece] = useState(bundle && initialByPiece);
  const lineUnit = saleLineUnit(product, byPiece);
  const measured = isMeasured(lineUnit.unitType);
  const unit = unitSuffix(lineUnit.unitType, lineUnit.unitLabel);
  const currentQuantity = quantityFor(byPiece);
  const inCart = currentQuantity > 0;
  const stockText = bundle
    ? formatBundleStock(product.stockPieces, product.piecesPerUnit)
    : `${formatQuantity(product.unitType, product.stockPieces)} ${unit}`;

  return (
    <AmountPadSheet
      // Re-mount on a mode switch so the typed value restarts from that line's cart quantity.
      key={byPiece ? "piece" : "unit"}
      title={product.name}
      subtitle={`${centsToPeso(lineUnit.priceCents)}/${unit} · ${stockText} left`}
      headerSlot={
        bundle && (
          <div className={styles["dialog-unit-toggle"]}>
            <SegmentedControl
              options={[
                { value: "bundle", label: t("checkout.sellByBundle", { pieces: product.piecesPerUnit }) },
                { value: "piece", label: t("checkout.sellByPiece") },
              ]}
              value={byPiece ? "piece" : "bundle"}
              onChange={(value) => setByPiece(value === "piece")}
            />
          </div>
        )
      }
      initialValue={inCart ? formatQuantity(lineUnit.unitType, currentQuantity) : ""}
      maxDecimals={measured ? 3 : 0}
      suffix={unit}
      presets={measured ? MEASURE_PRESETS.map((value) => ({ value, label: `${value} ${unit}` })) : []}
      renderFooter={(value) => (
        <div className={styles["dialog-total-row"]}>
          <div className={styles["dialog-total-label"]}>{t("checkout.subtotal")}</div>
          <div className={styles["dialog-total-value"]}>
            {centsToPeso(
              lineTotalCents(lineUnit.priceCents, parseQuantityInput(value, lineUnit.unitType), lineUnit.unitType),
            )}
          </div>
        </div>
      )}
      canConfirm={(value) => inCart || parseQuantityInput(value, lineUnit.unitType) > 0}
      confirmLabel={(value) => {
        if (!inCart) return t("checkout.addToCart");
        return parseQuantityInput(value, lineUnit.unitType) > 0 ? t("checkout.updateCart") : t("checkout.removeFromCart");
      }}
      onConfirm={(value) => onConfirm(parseQuantityInput(value, lineUnit.unitType), byPiece)}
      onClose={onClose}
    />
  );
}
