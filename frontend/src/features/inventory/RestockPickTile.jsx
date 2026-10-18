import { useState } from "react";

import ProductThumb from "../../components/ProductThumb";
import {
  centsToPesoInput,
  formatQuantity,
  isMeasured,
  parseQuantityInput,
  pesoInputToCents,
  sanitizePesoInput,
  sanitizeQuantityInput,
  unitSuffix,
} from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import styles from "./inventory.module.css";

export default function RestockPickTile({ product, amount, onAmountChange, onCostChange }) {
  const { t } = useAuth();
  const [costInput, setCostInput] = useState(centsToPesoInput(product.costCents));
  const measured = isMeasured(product.unitType);
  const unit = measured ? unitSuffix(product.unitType, product.unitLabel) : "pcs";
  // Local text so partial decimals like "1." survive while typing.
  const [input, setInput] = useState(amount ? formatQuantity(product.unitType, amount) : "");
  const selected = amount > 0;

  return (
    <div className={`${styles["pick-tile"]} ${selected ? styles["pick-tile-selected"] : ""}`}>
      <ProductThumb name={product.name} category={product.category} size="sm" />
      <div>
        <div className={styles["pick-tile-name"]}>{product.name}</div>
        <div className={styles["pick-tile-meta"]}>
          {formatQuantity(product.unitType, product.stockPieces)} {unit} in stock
        </div>
      </div>
      <div className={styles["pick-qty-row"]}>
        <span className={styles["pick-qty-prefix"]}>+</span>
        <input
          className={styles["pick-qty-input"]}
          inputMode={measured ? "decimal" : "numeric"}
          placeholder="0"
          aria-label={`Amount to add to ${product.name}`}
          value={input}
          onChange={(e) => {
            const next = sanitizeQuantityInput(e.target.value, product.unitType);
            setInput(next);
            onAmountChange(parseQuantityInput(next, product.unitType));
          }}
        />
        <div className={styles["pick-qty-suffix"]}>{unit}</div>
      </div>
      {selected && (
        <label className={styles["pick-cost-row"]}>
          <span>{t("inventory.unitCost", { unit: unitSuffix(product.unitType, product.unitLabel) })}</span>
          <span className={styles["pick-cost-input"]}>
            ₱
            <input
              inputMode="decimal"
              placeholder={t("inventory.optional")}
              aria-label={t("inventory.unitCostFor", { name: product.name })}
              value={costInput}
              onChange={(e) => {
                const next = sanitizePesoInput(e.target.value);
                setCostInput(next);
                onCostChange(pesoInputToCents(next));
              }}
            />
          </span>
        </label>
      )}
    </div>
  );
}
