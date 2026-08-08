import Avatar from "./Avatar";
import styles from "./chat.module.css";

export default function ConversationRow({ name, lastMessage, timeLabel, unreadCount, active, onOpen }) {
  return (
    <button type="button" className={`${styles.row} ${active ? styles["row-active"] : ""}`} onClick={onOpen}>
      <Avatar name={name} size="md" />
      <div className={styles["row-body"]}>
        <div className={styles["row-name"]}>{name}</div>
        <div className={styles["row-preview"]}>{lastMessage}</div>
      </div>
      <div className={styles["row-meta"]}>
        <span className={styles["row-time"]}>{timeLabel}</span>
        {unreadCount > 0 && <span className={styles["row-unread"]}>{unreadCount}</span>}
      </div>
    </button>
  );
}
