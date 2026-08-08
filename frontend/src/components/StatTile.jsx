import styles from "./primitives.module.css";

export default function StatTile({ label, value, subLabel }) {
  return (
    <div className={styles["stat-tile"]}>
      <div className={styles["stat-label"]}>{label}</div>
      <div className={styles["stat-value"]}>{value}</div>
      {subLabel && <div className={styles["stat-sub"]}>{subLabel}</div>}
    </div>
  );
}
