import styles from "./primitives.module.css";

// Primary actions for a page: sticky at the bottom of the screen on phones (thumb reach), inline on desktop.
// Place it as the last child of a page container that is `min-height: 100%` and a flex column.
export default function ActionBar({ children }) {
  return <div className={styles["action-bar"]}>{children}</div>;
}
