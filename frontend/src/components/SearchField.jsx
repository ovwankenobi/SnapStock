import Icon from "./Icon";
import styles from "./primitives.module.css";

export default function SearchField({ value, onChange, placeholder }) {
  return (
    <div className={styles["search-field"]}>
      <Icon name="search" size={16} />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
      />
    </div>
  );
}
