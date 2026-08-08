import { useState } from "react";

import AppLayout from "../../components/AppLayout";
import { buyerNavItems, sellerNavItems } from "../../lib/nav";
import { useAuth } from "./AuthContext";
import styles from "./auth.module.css";
import LanguageToggle from "./LanguageToggle";

const BUSINESS_TYPE_LABEL_KEYS = {
  retail: "auth.register.businessTypeRetail",
  wholesale: "auth.register.businessTypeWholesale",
  both: "auth.register.businessTypeBoth",
};

function draftFromUser(user) {
  return {
    fullName: user.fullName || "",
    phone: user.phone || "",
    businessName: user.sellerProfile?.businessName || "",
    businessType: user.sellerProfile?.businessType || "retail",
    address: user.sellerProfile?.address || "",
    description: user.sellerProfile?.description || "",
  };
}

export default function ProfilePage() {
  const { user, updateProfile, t } = useAuth();
  const isSeller = user.role === "seller";

  const [draft, setDraft] = useState(() => draftFromUser(user));
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");

  function updateField(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setStatus("saving");
    try {
      await updateProfile({
        fullName: draft.fullName,
        phone: draft.phone || null,
        ...(isSeller
          ? {
              businessName: draft.businessName,
              businessType: draft.businessType,
              address: draft.address || null,
              description: draft.description || null,
            }
          : {}),
      });
      setStatus("saved");
    } catch {
      setStatus("idle");
      setError("Could not save changes. Please try again.");
    }
  }

  return (
    <AppLayout navItems={isSeller ? sellerNavItems() : buyerNavItems()} title="Profile">
      <div className={styles["profile-page"]}>
        <div className={styles["profile-language"]}>
          <div className={styles["field-label"]}>{t("common.appName")} · {t("language.english")} / {t("language.tagalog")}</div>
          <LanguageToggle />
        </div>

        <form className={styles["auth-form"]} onSubmit={handleSubmit}>
          <div>
            <label className={styles["field-label"]} htmlFor="profile-email">
              Email
            </label>
            <input id="profile-email" className={styles["text-input"]} value={user.email} disabled />
          </div>
          <div>
            <label className={styles["field-label"]} htmlFor="profile-fullName">
              Full name
            </label>
            <input
              id="profile-fullName"
              className={styles["text-input"]}
              required
              value={draft.fullName}
              onChange={(event) => updateField("fullName", event.target.value)}
            />
          </div>
          <div>
            <label className={styles["field-label"]} htmlFor="profile-phone">
              Phone
            </label>
            <input
              id="profile-phone"
              className={styles["text-input"]}
              value={draft.phone}
              onChange={(event) => updateField("phone", event.target.value)}
            />
          </div>

          {isSeller && (
            <>
              <div>
                <label className={styles["field-label"]} htmlFor="profile-businessName">
                  Business name
                </label>
                <input
                  id="profile-businessName"
                  className={styles["text-input"]}
                  required
                  value={draft.businessName}
                  onChange={(event) => updateField("businessName", event.target.value)}
                />
              </div>
              <div>
                <div className={styles["field-label"]}>Business type</div>
                <div className={styles["chip-row"]}>
                  {Object.keys(BUSINESS_TYPE_LABEL_KEYS).map((type) => (
                    <button
                      key={type}
                      type="button"
                      className={`${styles["type-toggle"]} ${draft.businessType === type ? styles["type-toggle-active"] : ""}`}
                      onClick={() => updateField("businessType", type)}
                    >
                      {t(BUSINESS_TYPE_LABEL_KEYS[type])}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className={styles["field-label"]} htmlFor="profile-address">
                  Address
                </label>
                <input
                  id="profile-address"
                  className={styles["text-input"]}
                  value={draft.address}
                  onChange={(event) => updateField("address", event.target.value)}
                />
              </div>
              <div>
                <label className={styles["field-label"]} htmlFor="profile-description">
                  Description
                </label>
                <textarea
                  id="profile-description"
                  className={styles.textarea}
                  value={draft.description}
                  onChange={(event) => updateField("description", event.target.value)}
                />
              </div>
            </>
          )}

          {error && (
            <div className={styles["form-error"]} role="alert">
              {error}
            </div>
          )}

          <button type="submit" className={styles["submit-button"]} disabled={status === "saving"}>
            {status === "saving" ? "Saving..." : status === "saved" ? "Saved" : "Save Changes"}
          </button>
        </form>
      </div>
    </AppLayout>
  );
}
