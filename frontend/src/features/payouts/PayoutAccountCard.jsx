import { mediaUrl } from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import { payoutAccountTitle } from "./payoutFormat";
import styles from "./payouts.module.css";

// `stacked` shows a large, scannable QR for buyers; the default compact row is for the seller's own list.
export default function PayoutAccountCard({ account, stacked = false, showDefault = false, children }) {
  const { t } = useAuth();
  const title = payoutAccountTitle(t, account);

  return (
    <div className={`${styles.card} ${stacked ? styles["card-stacked"] : ""}`}>
      {account.qrUrl ? (
        <img className={styles["card-qr"]} src={mediaUrl(account.qrUrl)} alt={`${title} QR`} />
      ) : (
        !stacked && <div className={styles["card-qr-missing"]}>{t("payouts.noQr")}</div>
      )}
      <div className={styles["card-body"]}>
        <div className={styles["card-title"]}>
          {title}
          {showDefault && account.isDefault && <span className={styles["default-badge"]}>{t("payouts.default")}</span>}
        </div>
        <div className={styles["card-name"]}>{account.accountName}</div>
        <div className={styles["card-number"]}>{account.accountNumber}</div>
        {children}
      </div>
    </div>
  );
}
