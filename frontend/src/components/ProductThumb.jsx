import { colorForKey } from "../lib/format";
import styles from "./primitives.module.css";

export default function ProductThumb({ name, category, size = "md", photoUrl }) {
  if (photoUrl) {
    return (
      <img
        className={`${styles.thumb} ${styles[`thumb-${size}`]} ${styles["thumb-photo"]}`}
        src={photoUrl}
        alt={name || ""}
      />
    );
  }

  const label = (category || name || "?").charAt(0).toUpperCase();
  return (
    <div className={`${styles.thumb} ${styles[`thumb-${size}`]}`} style={{ background: colorForKey(category || name) }}>
      {label}
    </div>
  );
}
