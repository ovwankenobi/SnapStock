import Icon from "./Icon";
import styles from "./primitives.module.css";

export default function IconButton({ icon, onClick, label, variant = "ghost" }) {
  return (
    <button type="button" className={`${styles["icon-button"]} ${styles[`icon-button-${variant}`]}`} onClick={onClick} aria-label={label}>
      <Icon name={icon} size={17} />
    </button>
  );
}
