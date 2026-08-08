import { colorForKey, initials } from "../lib/format";
import styles from "./primitives.module.css";

export default function Avatar({ name, size = "sm" }) {
  return (
    <div className={`${styles.avatar} ${styles[`avatar-${size}`]}`} style={{ background: colorForKey(name) }}>
      {initials(name)}
    </div>
  );
}
