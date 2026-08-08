import Icon from "../../components/Icon";
import styles from "./auth.module.css";

export default function RoleOptionCard({ icon, title, description, primary, onSelect }) {
  return (
    <button
      type="button"
      className={`${styles["role-card"]} ${primary ? styles["role-card-primary"] : ""}`}
      onClick={onSelect}
    >
      <span className={styles["role-icon"]}>
        <Icon name={icon} size={22} />
      </span>
      <span>
        <div className={styles["role-title"]}>{title}</div>
        <div className={styles["role-description"]}>{description}</div>
      </span>
    </button>
  );
}
