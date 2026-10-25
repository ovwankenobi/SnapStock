import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getCatalogSeller } from "../../api/catalog";
import MeasureInput from "../../components/MeasureInput";
import QuantityStepper from "../../components/QuantityStepper";
import SegmentedControl from "../../components/SegmentedControl";
import Sheet from "../../components/Sheet";
import { centsToPeso, isBundle, isMeasured, lineTotalCents, parseQuantityInput, unitSuffix } from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import PaymentMethodPicker from "../payouts/PaymentMethodPicker";
import { saleLineUnit } from "../sales/salesFormat";
import styles from "./buyer.module.css";

export default function BuySheet({ product, onConfirm, onClose, isSubmitting, error }) {
  const { t } = useAuth();
  const bundle = isBundle(product.unitType);
  const [byPiece, setByPiece] = useState(false);
  const lineUnit = saleLineUnit(product, byPiece);
  const measured = isMeasured(product.unitType);
  const [quantity, setQuantity] = useState(1);
  const [measureInput, setMeasureInput] = useState("1");
  const [paymentMethod, setPaymentMethod] = useState("cash");

  // Same key as SellerPage, so the seller's payout accounts are usually already cached.
  const { data: seller } = useQuery({
    queryKey: ["catalogSeller", product.sellerId],
    queryFn: () => getCatalogSeller(product.sellerId),
  });

  const unit = unitSuffix(lineUnit.unitType, lineUnit.unitLabel);
  const saleQuantity = measured ? parseQuantityInput(measureInput, product.unitType) : quantity;
  const total = lineTotalCents(lineUnit.priceCents, saleQuantity, lineUnit.unitType);

  return (
    <Sheet onClose={onClose} centered label={product.name}>
      <div className={styles["sheet-title"]}>{product.name}</div>
      <div className={styles["sheet-sub"]}>
        {centsToPeso(lineUnit.priceCents)}/{unit}
      </div>

      {bundle && (
        <SegmentedControl
          options={[
            { value: "bundle", label: t("checkout.sellByBundle", { pieces: product.piecesPerUnit }) },
            { value: "piece", label: t("checkout.sellByPiece") },
          ]}
          value={byPiece ? "piece" : "bundle"}
          onChange={(value) => setByPiece(value === "piece")}
        />
      )}

      {measured ? (
        <MeasureInput value={measureInput} onChange={setMeasureInput} unitLabel={unit} />
      ) : (
        <QuantityStepper
          quantity={quantity}
          onIncrement={() => setQuantity((qty) => qty + 1)}
          onDecrement={() => setQuantity((qty) => Math.max(1, qty - 1))}
        />
      )}

      <PaymentMethodPicker
        accounts={seller?.payoutAccounts}
        value={paymentMethod}
        onChange={setPaymentMethod}
      />

      <div className={styles["sheet-total"]}>Total: {centsToPeso(total)}</div>

      {error && <div className={styles["sheet-error"]}>{error}</div>}

      <button
        type="button"
        className={styles["sheet-submit"]}
        disabled={isSubmitting || saleQuantity <= 0}
        onClick={() => onConfirm({ quantity: saleQuantity, paymentMethod, byPiece: byPiece || undefined })}
      >
        {isSubmitting ? t("orders.placingOrder") : t("orders.placeOrder")}
      </button>
    </Sheet>
  );
}
