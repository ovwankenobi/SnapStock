import { useNavigate } from "react-router-dom";

import Icon from "../../components/Icon";
import { useAuth } from "../auth/AuthContext";
import { usePendingOrders } from "../sales/usePendingOrders";
import styles from "./dashboard.module.css";

export default function PendingOrdersBanner() {
  const { t } = useAuth();
  const navigate = useNavigate();
  const { data } = usePendingOrders();

  const count = data?.total || 0;
  if (count === 0) return null;

  return (
    <div className={styles["low-stock-banner"]}>
      <button type="button" className={styles["low-stock-banner-body"]} onClick={() => navigate("/sales?path=account")}>
        <Icon name="warning" size={16} color="var(--color-warning)" />
        <span>{count === 1 ? t("orders.nudgeOne") : t("orders.nudgeMany", { count })}</span>
      </button>
    </div>
  );
}
