import Icon from "../../components/Icon";
import styles from "./dashboard.module.css";

export default function PinnableCard({ pinned, isCustomizing, onToggle, children }) {
  return (
    <div className={styles["pinnable-card"]}>
      {children}
      {isCustomizing && (
        <button
          type="button"
          className={`${styles["pin-toggle"]} ${pinned ? styles["pin-toggle-active"] : ""}`}
          onClick={onToggle}
          aria-label={pinned ? "Unpin from top" : "Pin to top"}
        >
          <Icon name="pin" size={13} />
        </button>
      )}
    </div>
  );
}
