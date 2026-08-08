import styles from "./primitives.module.css";

export default function Badge({ tone = "neutral", children }) {
  return <span className={`${styles.badge} ${styles[`badge-${tone}`]}`}>{children}</span>;
}
