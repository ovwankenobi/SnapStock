import Icon from "../../components/Icon";
import ProductThumb from "../../components/ProductThumb";
import { isMeasured, mediaUrl, pesoInputToCents, sanitizePesoInput, sanitizeQuantityInput } from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import CategorySelect from "./CategorySelect";
import styles from "./inventory.module.css";

const UNIT_OPTIONS = [
  { value: "piece", label: "Per Piece" },
  { value: "bundle", label: "Bundle" },
  { value: "measure", label: "Per Unit" },
];
const UNIT_LABEL_PRESETS = ["kg", "g", "m", "cm", "ft", "yd", "L"];

export default function ProductForm({
  value,
  onFieldChange,
  onSubmit,
  onPhotoSelect,
  submitLabel = "Save Product",
  isSubmitting = false,
}) {
  const { t } = useAuth();
  const measured = isMeasured(value.unitType);
  const priceCents = Number(value.priceInput) * 100;
  const costCents = pesoInputToCents(value.costInput);
  const marginPct = priceCents > 0 && costCents != null ? Math.round(((priceCents - costCents) / priceCents) * 100) : null;
  const isCustomUnitLabel = !UNIT_LABEL_PRESETS.includes(value.unitLabel);
  const stockUnit = measured ? value.unitLabel || "unit" : "pieces";

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
          <CategorySelect value={value.category} onChange={(category) => onFieldChange("category", category)} />
        </div>
      </div>

      <div>
        <div className={styles["field-label"]}>{t("inventory.costPrice")}</div>
        <input
          className={styles["text-input"]}
          inputMode="decimal"
          placeholder={t("inventory.optional")}
          value={value.costInput}
          onChange={(e) => onFieldChange("costInput", sanitizePesoInput(e.target.value))}
        />
        <div className={`${styles["field-hint"]} ${marginPct != null && marginPct <= 0 ? styles["field-hint-danger"] : ""}`}>
          {marginPct == null ? t("inventory.costHint") : t("inventory.marginHint", { pct: marginPct })}
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

      {measured && (
        <div>
          <div className={styles["field-label"]}>Unit of Measure</div>
          <div className={styles["chip-row"]}>
            {UNIT_LABEL_PRESETS.map((label) => (
              <button
                key={label}
                type="button"
                className={`${styles["unit-toggle"]} ${value.unitLabel === label ? styles["unit-toggle-active"] : ""}`}
                onClick={() => onFieldChange("unitLabel", label)}
              >
                {label}
              </button>
            ))}
          </div>
          <input
            className={`${styles["text-input"]} ${styles["unit-label-input"]}`}
            placeholder="Other unit (e.g. sack, gallon)"
            maxLength={16}
            value={isCustomUnitLabel ? value.unitLabel : ""}
            onChange={(e) => onFieldChange("unitLabel", e.target.value)}
            required={isCustomUnitLabel}
          />
        </div>
      )}

      {value.unitType === "bundle" && (
        <div>
          <div className={styles["field-label"]}>Pieces per Bundle</div>
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
        {!value.hideStock && (
          <div className={styles.field}>
            <div className={styles["field-label"]}>Starting Stock ({stockUnit})</div>
            <input
              className={styles["text-input"]}
              inputMode={measured ? "decimal" : "numeric"}
              value={value.stockInput}
              onChange={(e) => onFieldChange("stockInput", sanitizeQuantityInput(e.target.value, value.unitType))}
            />
          </div>
        )}
        <div className={styles.field}>
          <div className={styles["field-label"]}>Low Stock Threshold{measured ? ` (${stockUnit})` : ""}</div>
          <input
            className={styles["text-input"]}
            inputMode={measured ? "decimal" : "numeric"}
            value={value.lowStockThresholdInput}
            onChange={(e) =>
              onFieldChange("lowStockThresholdInput", sanitizeQuantityInput(e.target.value, value.unitType))
            }
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

      <button type="submit" className={`${styles["submit-button"]} ${styles["form-submit"]}`} disabled={isSubmitting}>
        {isSubmitting ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}
