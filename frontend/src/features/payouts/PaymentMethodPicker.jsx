import SegmentedControl from "../../components/SegmentedControl";
import { useAuth } from "../auth/AuthContext";
import PayoutAccountCard from "./PayoutAccountCard";
import { PAYOUT_METHODS, payoutMethodLabel } from "./payoutFormat";
import styles from "./payouts.module.css";

// Every method a sale can record. Cash is always available; the rest are grayed out
// until the seller has a payout account for them.
const PAYMENT_METHODS = ["cash", ...PAYOUT_METHODS];

function paymentOptions(t, accounts) {
  const available = new Set(["cash", ...accounts.map((account) => account.method)]);
  return PAYMENT_METHODS.map((method) => ({
    value: method,
    label: method === "cash" ? t("payouts.cash") : payoutMethodLabel(t, method),
    disabled: !available.has(method),
  }));
}

// Payment method selector plus the seller's matching payout QR(s), shown to buyers paying
// in-app and on the seller's own screen so a walk-in customer can scan it.
export default function PaymentMethodPicker({ accounts = [], value, onChange, hint }) {
  const { t } = useAuth();
  const matchingAccounts = accounts.filter((account) => account.method === value);

  return (
    <>
      <div className={styles["method-picker"]}>
        <SegmentedControl options={paymentOptions(t, accounts)} value={value} onChange={onChange} />
      </div>

      {matchingAccounts.length > 0 && (
        <div className={styles["pay-panel"]}>
          <div className={styles["pay-hint"]}>{hint || t("payouts.scanHint")}</div>
          {matchingAccounts.map((account) => (
            <PayoutAccountCard key={account.id} account={account} stacked />
          ))}
        </div>
      )}
    </>
  );
}
