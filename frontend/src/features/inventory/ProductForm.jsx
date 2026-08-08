import Icon from "../../components/Icon";
import ProductThumb from "../../components/ProductThumb";
import { mediaUrl } from "../../lib/format";
import styles from "./inventory.module.css";

const UNIT_OPTIONS = [
  { value: "piece", label: "Per Piece" },
  { value: "bundle", label: "Bundle" },
  { value: "grams", label: "Per Kilo" },
];

export default function ProductForm({
  value,
  onFieldChange,
  onSubmit,
  onPhotoSelect,
  submitLabel = "Save Product",
  isSubmitting = false,
}) {
  const showPiecesPerUnit = value.unitType === "bundle" || value.unitType === "grams";
  const piecesPerUnitLabel = value.unitType === "grams" ? "Grams per Kilo Sold" : "Pieces per Bundle";

  return (
    <form
      className={styles["form-panel"]}
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <label className={styles["photo-drop"]}>
        {value.photoUrl ? (
          <ProductThumb name={value.name} photoUrl={mediaUrl(value.photoUrl)} size="lg" />
        ) : (
          <>
            <Icon name="camera" size={28} />
            <span>Tap to add photo</span>
          </>
        )}
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          hidden
          onChange={(e) => e.target.files[0] && onPhotoSelect?.(e.target.files[0])}
        />
      </label>

      <div>
        <div className={styles["field-label"]}>Product Name</div>
        <input
          className={styles["text-input"]}
          value={value.name}
          onChange={(e) => onFieldChange("name", e.target.value)}
          required
        />
      </div>

      <div className={styles["field-row"]}>
        <div className={styles.field}>
          <div className={styles["field-label"]}>Price (₱)</div>
          <input
            className={styles["text-input"]}
            inputMode="numeric"
            value={value.priceInput}
            onChange={(e) => onFieldChange("priceInput", e.target.value.replace(/[^0-9]/g, ""))}
            required
          />
        </div>
        <div className={styles.field}>
          <div className={styles["field-label"]}>Category</div>
          <input
            className={styles["text-input"]}
            value={value.category}
            onChange={(e) => onFieldChange("category", e.target.value)}
          />
        </div>
      </div>

      <div>
        <div className={styles["field-label"]}>Unit Type</div>
        <div className={styles["chip-row"]}>
          {UNIT_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`${styles["unit-toggle"]} ${value.unitType === option.value ? styles["unit-toggle-active"] : ""}`}
              onClick={() => onFieldChange("unitType", option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {showPiecesPerUnit && (
        <div>
          <div className={styles["field-label"]}>{piecesPerUnitLabel}</div>
          <input
            className={styles["text-input"]}
            inputMode="numeric"
            value={value.piecesPerUnitInput}
            onChange={(e) => onFieldChange("piecesPerUnitInput", e.target.value.replace(/[^0-9]/g, ""))}
            required
          />
        </div>
      )}

      <div className={styles["field-row"]}>
        <div className={styles.field}>
          <div className={styles["field-label"]}>Starting Stock (pieces)</div>
          <input
            className={styles["text-input"]}
            inputMode="numeric"
            value={value.stockInput}
            onChange={(e) => onFieldChange("stockInput", e.target.value.replace(/[^0-9]/g, ""))}
            disabled={value.disableStock}
          />
        </div>
        <div className={styles.field}>
          <div className={styles["field-label"]}>Low Stock Threshold</div>
          <input
            className={styles["text-input"]}
            inputMode="numeric"
            value={value.lowStockThresholdInput}
            onChange={(e) => onFieldChange("lowStockThresholdInput", e.target.value.replace(/[^0-9]/g, ""))}
          />
        </div>
      </div>

      <div>
        <div className={styles["field-label"]}>Description</div>
        <textarea
          className={styles.textarea}
          value={value.description}
          onChange={(e) => onFieldChange("description", e.target.value)}
        />
      </div>

      <button type="submit" className={styles["submit-button"]} disabled={isSubmitting}>
        {isSubmitting ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}
