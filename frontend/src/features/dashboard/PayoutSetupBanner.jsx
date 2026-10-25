import { useState } from "react";
import { useNavigate } from "react-router-dom";

import Icon from "../../components/Icon";
import { useAuth } from "../auth/AuthContext";
import styles from "./dashboard.module.css";

export default function PayoutSetupBanner() {
  const { user, t } = useAuth();
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState(false);

  const accounts = user?.sellerProfile?.payoutAccounts;
  if (dismissed || !accounts || accounts.length > 0) return null;

  return (
    <div className={styles["low-stock-banner"]}>
      <button type="button" className={styles["low-stock-banner-body"]} onClick={() => navigate("/profile?tab=payment")}>
        <Icon name="warning" size={16} color="var(--color-warning)" />
        <span>{t("payouts.nudge")}</span>
      </button>
      <button
        type="button"
        className={styles["low-stock-banner-dismiss"]}
        onClick={() => setDismissed(true)}
        aria-label="Dismiss"
      >
        <Icon name="close" size={14} />
      </button>
    </div>
  );
}
