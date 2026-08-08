import Icon from "../../components/Icon";
import styles from "./dashboard.module.css";

export default function LowStockAlert({ count, productNames, onClick }) {
  return (
    <button type="button" className={styles["low-stock"]} onClick={onClick}>
      <div className={styles["low-stock-heading"]}>
        <Icon name="warning" size={16} color="var(--color-warning)" />
        <span className={styles["low-stock-count"]}>{count}</span>
        <span className={styles["low-stock-label"]}>Low Stock</span>
      </div>
      <div className={styles["low-stock-names"]}>{productNames.join(", ")}</div>
    </button>
  );
}
