import { NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../features/auth/AuthContext";
import { usePendingOrders } from "../features/sales/usePendingOrders";
import { useTheme } from "../hooks/useTheme";
import { useUnreadMessageCount } from "../hooks/useUnreadMessageCount";
import BottomNav from "./BottomNav";
import Icon from "./Icon";
import IconButton from "./IconButton";
import { LogoMark, LogoWordmark } from "./Logo";
import styles from "./AppLayout.module.css";

// Phone (<768px): app bar + bottom tab bar. Tablet: icon rail. Desktop (>=1024px): full sidebar.
// `backTo` (a path, -1 for history back, or a callback for in-page views) shows a back button before the title.
// `hideBottomNav` is for focused screens (chat, forms, pickers) that own the bottom of the screen.
export default function AppLayout({ navItems, title, headerAction, brandLabel, backTo, hideBottomNav, children }) {
  const { user, logout, t } = useAuth();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const unreadMessageCount = useUnreadMessageCount();
  // Online orders waiting for approval badge the Sell item, which opens them under Buyer Account.
  const { data: pendingOrders } = usePendingOrders({ enabled: user?.role === "seller" });
  const pendingOrderCount = user?.role === "seller" ? pendingOrders?.total || 0 : 0;
  const fullName = user?.fullName?.trim();
  const resolvedNavItems = navItems.map((item) => ({
    ...item,
    label: item.showUserName && fullName ? fullName : t(item.labelKey),
    shortLabel: item.showUserName && fullName ? fullName.split(/\s+/)[0] : t(item.shortLabelKey || item.labelKey),
    badge: item.icon === "chat" ? unreadMessageCount : item.to === "/sales" ? pendingOrderCount : item.badge,
  }));

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className={`${styles.shell} ${hideBottomNav ? styles["shell-no-bottom-nav"] : ""}`}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <LogoMark size={36} className={styles["brand-mark"]} />
          <LogoWordmark height={20} className={styles["brand-name"]} />
        </div>
        <nav className={styles.nav}>
          {resolvedNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              title={item.label}
              className={({ isActive }) => `${styles["nav-item"]} ${isActive ? styles["nav-item-active"] : ""}`}
            >
              <span className={styles["nav-icon"]}>
                <Icon name={item.icon} size={20} color="currentColor" />
                {item.badge > 0 && <span className={styles["nav-badge"]}>{item.badge}</span>}
              </span>
              <span className={styles["nav-label"]}>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        {brandLabel && <div className={styles["sidebar-footer"]}>{brandLabel}</div>}
      </aside>
      <div className={styles.main}>
        <header className={styles.header}>
          {backTo != null && (
            <IconButton
              icon="back"
              label={t("nav.back")}
              onClick={() => {
                if (typeof backTo === "function") backTo();
                else navigate(backTo);
              }}
            />
          )}
          <h1 className={styles["header-title"]}>{title}</h1>
          {headerAction}
          <div className={styles["header-desktop-actions"]}>
            <IconButton
              icon={theme === "dark" ? "sun" : "moon"}
              label={theme === "dark" ? t("nav.lightMode") : t("nav.darkMode")}
              onClick={toggleTheme}
            />
            <IconButton icon="logout" label={t("nav.logout")} onClick={handleLogout} />
          </div>
        </header>
        <main className={styles.content}>{children}</main>
      </div>
      {!hideBottomNav && <BottomNav items={resolvedNavItems} />}
    </div>
  );
}
