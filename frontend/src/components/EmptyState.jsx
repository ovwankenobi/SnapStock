import styles from "./primitives.module.css";

export default function EmptyState({ message }) {
  return <div className={styles["empty-state"]}>{message}</div>;
}
