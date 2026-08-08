import styles from "./primitives.module.css";

export default function LoadingState({ message = "Loading…" }) {
  return (
    <div className={styles["loading-state"]} role="status" aria-live="polite">
      <span className={styles.spinner} aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}
