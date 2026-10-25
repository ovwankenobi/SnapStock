import { useState } from "react";

import MeasureInput from "../../components/MeasureInput";
import QuantityStepper from "../../components/QuantityStepper";
import Sheet from "../../components/Sheet";
import {
  centsToPeso,
  formatQuantity,
  isMeasured,
  lineTotalCents,
  parseQuantityInput,
  unitSuffix,
} from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import PaymentMethodPicker from "../payouts/PaymentMethodPicker";
import QrPayScreen, { qrAccountsFor } from "../payouts/QrPayScreen";
import PriceEditor from "../sales/PriceEditor";
import styles from "./inventory.module.css";

export default function QuickSellSheet({ product, onConfirm, onClose, isSubmitting, error }) {
  const measured = isMeasured(product.unitType);
  const [quantity, setQuantity] = useState(1);
  const [measureInput, setMeasureInput] = useState("1");
  const [paymentMethod, setPaymentMethod] = useState("cash");
  // Agreed price for this sale only; null = the product's list price.
  const [unitPriceCents, setUnitPriceCents] = useState(null);
  // Full-screen QR step before a non-cash sale is recorded.
  const [showQr, setShowQr] = useState(false);
  const { user, t } = useAuth();

  const unit = unitSuffix(product.unitType, product.unitLabel);
  const maxQuantity = Math.max(1, Math.floor(product.stockPieces / product.piecesPerUnit));
  const saleQuantity = measured ? parseQuantityInput(measureInput, product.unitType) : quantity;
  const total = lineTotalCents(unitPriceCents ?? product.priceCents, saleQuantity, product.unitType);
  const qrAccounts = qrAccountsFor(user?.sellerProfile?.payoutAccounts, paymentMethod);

  // The whole payload (including an edited price) is what the offline queue replays.
  function confirmSale() {
    onConfirm({ quantity: saleQuantity, paymentMethod, unitPriceCents: unitPriceCents ?? undefined });
  }

  if (showQr && qrAccounts.length > 0) {
    return (
      <QrPayScreen
        accounts={qrAccounts}
        totalCents={total}
        onConfirm={confirmSale}
        onBack={() => setShowQr(false)}
        isSubmitting={isSubmitting}
        error={error}
      />
    );
  }

  return (
    <Sheet onClose={onClose} centered label={product.name}>
      <div className={styles["sheet-title"]}>{product.name}</div>
      <div className={styles["sheet-sub"]}>
        {formatQuantity(product.unitType, product.stockPieces)} {unit} available
      </div>

      {measured ? (
        <MeasureInput value={measureInput} onChange={setMeasureInput} unitLabel={unit} />
      ) : (
        <QuantityStepper
          quantity={quantity}
          onIncrement={() => setQuantity((qty) => Math.min(qty + 1, maxQuantity))}
          onDecrement={() => setQuantity((qty) => Math.max(1, qty - 1))}
        />
      )}

      <PriceEditor
        listPriceCents={product.priceCents}
        priceCents={unitPriceCents ?? product.priceCents}
        costCents={product.costCents}
        unitLabel={unit}
        onChange={setUnitPriceCents}
      />

      <PaymentMethodPicker
        accounts={user?.sellerProfile?.payoutAccounts}
        value={paymentMethod}
        onChange={setPaymentMethod}
        hint={t("payouts.showToBuyerHint")}
      />

      <div className={styles["sheet-total"]}>Total: {centsToPeso(total)}</div>

      {error && <div className={styles["sheet-error"]}>{error}</div>}

      <button
        type="button"
        className={styles["sheet-submit"]}
        disabled={isSubmitting || saleQuantity <= 0}
        onClick={qrAccounts.length > 0 ? () => setShowQr(true) : confirmSale}
      >
        {isSubmitting ? "Selling..." : "Confirm Sale"}
      </button>
    </Sheet>
  );
}
