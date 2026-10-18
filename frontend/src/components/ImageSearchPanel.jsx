import { useState } from "react";

import IconButton from "./IconButton";
import styles from "./ImageSearchPanel.module.css";

export default function ImageSearchPanel({
  onSubmit,
  onClose,
  isSubmitting,
  error,
  hint = "Snap or upload a photo, then tell us what it is — we'll match it to listings.",
  placeholder = "What is it? e.g. pork belly",
}) {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState("");

  const canSubmit = Boolean(file) && query.trim().length > 0 && !isSubmitting;

  return (
    <div className={styles["image-search-panel"]}>
      <div className={styles["image-search-header"]}>
        <div>
          <div className={styles["image-search-title"]}>Search by photo</div>
          <div className={styles["image-search-hint"]}>{hint}</div>
        </div>
        <IconButton icon="close" label="Close photo search" onClick={onClose} />
      </div>

      <label className={styles["image-search-drop"]}>
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          hidden
        />
        {file ? file.name : "Tap to choose a photo"}
      </label>

      <input
        className={styles["image-search-query"]}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={placeholder}
      />

      {error && <div className={styles["image-search-error"]}>{error}</div>}

      <button
        type="button"
        className={styles["image-search-submit"]}
        disabled={!canSubmit}
        onClick={() => onSubmit(file, query.trim())}
      >
        {isSubmitting ? "Searching..." : "Search"}
      </button>
    </div>
  );
}
