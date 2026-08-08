import { Link } from "react-router-dom";

import Icon from "../../components/Icon";
import styles from "./dashboard.module.css";

export default function QuickActionTile({ to, icon, label, badge }) {
  return (
    <Link to={to} className={styles["quick-action"]}>
      {badge > 0 && <span className={styles["quick-action-badge"]}>{badge}</span>}
      <span className={styles["quick-action-icon"]}>
        <Icon name={icon} size={20} />
      </span>
      <span className={styles["quick-action-label"]}>{label}</span>
    </Link>
  );
}
