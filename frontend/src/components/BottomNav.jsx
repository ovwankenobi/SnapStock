import { NavLink } from "react-router-dom";

import Icon from "./Icon";
import styles from "./AppLayout.module.css";

// Phone-only tab bar; hidden by CSS at >=768px where the sidebar takes over.
export default function BottomNav({ items }) {
  return (
    <nav className={styles["bottom-nav"]}>
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) =>
            `${styles["bottom-nav-item"]} ${isActive ? styles["bottom-nav-item-active"] : ""}`
          }
        >
          <span className={item.primary ? styles["bottom-nav-primary"] : styles["bottom-nav-icon"]}>
            <Icon name={item.icon} size={item.primary ? 24 : 22} color="currentColor" />
            {item.badge > 0 && <span className={styles["nav-badge"]}>{item.badge}</span>}
          </span>
          <span className={styles["bottom-nav-label"]}>{item.shortLabel}</span>
        </NavLink>
      ))}
    </nav>
  );
}
