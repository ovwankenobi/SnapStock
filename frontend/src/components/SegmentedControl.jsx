import styles from "./primitives.module.css";

export default function SegmentedControl({ options, value, onChange }) {
  return (
    <div className={styles.segmented}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={`${styles["segmented-option"]} ${option.value === value ? styles["segmented-option-active"] : ""}`}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
