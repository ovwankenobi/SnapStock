import { NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../features/auth/AuthContext";
import { useTheme } from "../hooks/useTheme";
import { useUnreadMessageCount } from "../hooks/useUnreadMessageCount";
import Icon from "./Icon";
import IconButton from "./IconButton";
import styles from "./AppLayout.module.css";

export default function AppLayout({ navItems, title, headerAction, brandLabel, children }) {
  const { logout, t } = useAuth();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const unreadMessageCount = useUnreadMessageCount();
  const resolvedNavItems = navItems.map((item) =>
    item.icon === "chat" ? { ...item, badge: unreadMessageCount } : item,
  );

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <div className={styles["brand-mark"]}>S</div>
          <div className={styles["brand-name"]}>SnapStock</div>
        </div>
        <nav className={styles.nav}>
          {resolvedNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `${styles["nav-item"]} ${isActive ? styles["nav-item-active"] : ""}`}
            >
              <span className={styles["nav-icon"]}>
                <Icon name={item.icon} size={20} color="currentColor" />
                {item.badge > 0 && <span className={styles["nav-badge"]}>{item.badge}</span>}
              </span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        {brandLabel && <div className={styles["sidebar-footer"]}>{brandLabel}</div>}
      </aside>
      <div className={styles.main}>
        <header className={styles.header}>
          <h1 className={styles["header-title"]}>{title}</h1>
          {headerAction}
          <IconButton
            icon={theme === "dark" ? "sun" : "moon"}
            label={theme === "dark" ? t("nav.lightMode") : t("nav.darkMode")}
            onClick={toggleTheme}
          />
          <IconButton icon="logout" label={t("nav.logout")} onClick={handleLogout} />
        </header>
        <div className={styles.content}>{children}</div>
      </div>
    </div>
  );
}
