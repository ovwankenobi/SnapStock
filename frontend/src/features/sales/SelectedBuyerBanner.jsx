import Avatar from "../../components/Avatar";
import styles from "./sales.module.css";

export default function SelectedBuyerBanner({ buyer, onClear }) {
  return (
    <div className={styles["selected-buyer"]}>
      <Avatar name={buyer.fullName} size="sm" />
      <span className={styles["selected-buyer-name"]}>{buyer.fullName}</span>
      <button type="button" className={styles["selected-buyer-clear"]} onClick={onClear}>
        Cancel
      </button>
    </div>
  );
}
