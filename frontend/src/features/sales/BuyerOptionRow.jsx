import Avatar from "../../components/Avatar";
import styles from "./sales.module.css";

export default function BuyerOptionRow({ buyer, onSelect }) {
  return (
    <button type="button" className={styles["buyer-row"]} onClick={() => onSelect(buyer)}>
      <Avatar name={buyer.fullName} size="sm" />
      <span className={styles["buyer-row-body"]}>
        <span className={styles["buyer-row-name"]}>{buyer.fullName}</span>
        <span className={styles["buyer-row-sub"]}>{buyer.phone || buyer.email}</span>
      </span>
    </button>
  );
}
