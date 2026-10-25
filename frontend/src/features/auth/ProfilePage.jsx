import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import AppLayout from "../../components/AppLayout";
import Icon from "../../components/Icon";
import SegmentedControl from "../../components/SegmentedControl";
import { useTheme } from "../../hooks/useTheme";
import { buyerNavItems, sellerNavItems } from "../../lib/nav";
import PayoutAccountsSection from "../payouts/PayoutAccountsSection";
import { useAuth } from "./AuthContext";
import ChangePasswordSection from "./ChangePasswordSection";
import styles from "./auth.module.css";
import LanguageToggle from "./LanguageToggle";
import QrLoginCard from "./QrLoginCard";

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
  const { user, updateProfile, logout, t } = useAuth();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const isSeller = user.role === "seller";
  // Buyers have no payout accounts, so they only get Profile and Security.
  const tabs = isSeller ? ["profile", "payment", "security"] : ["profile", "security"];
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = tabs.includes(searchParams.get("tab")) ? searchParams.get("tab") : "profile";

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

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
        <SegmentedControl
          options={tabs.map((value) => ({ value, label: t(`profile.tabs.${value}`) }))}
          value={tab}
          onChange={(value) => setSearchParams({ tab: value }, { replace: true })}
        />

        {tab === "profile" && (
          <>
            <div className={styles["profile-language"]}>
              <div className={styles["field-label"]}>{t("common.appName")} · {t("language.english")} / {t("language.tagalog")}</div>
              <LanguageToggle />
            </div>

            <form id="profile-form" className={styles["auth-form"]} onSubmit={handleSubmit}>
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

            </form>

            {error && (
              <div className={styles["form-error"]} role="alert">
                {error}
              </div>
            )}

            <button
              type="submit"
              form="profile-form"
              className={styles["submit-button"]}
              disabled={status === "saving"}
            >
              {status === "saving" ? "Saving..." : status === "saved" ? "Saved" : "Save Changes"}
            </button>
          </>
        )}

        {tab === "payment" && <PayoutAccountsSection />}

        {tab === "security" && (
          <>
            <ChangePasswordSection />
            <QrLoginCard />
          </>
        )}

        <div className={styles["profile-account"]}>
          <div className={styles["field-label"]}>{t("nav.account")}</div>
          <button type="button" className={styles["profile-account-row"]} onClick={toggleTheme}>
            {t("nav.darkModeLabel")}
            <Icon name={theme === "dark" ? "sun" : "moon"} size={20} />
          </button>
          <button
            type="button"
            className={`${styles["profile-account-row"]} ${styles["profile-logout"]}`}
            onClick={handleLogout}
          >
            {t("nav.logout")}
            <Icon name="logout" size={20} />
          </button>
        </div>
      </div>
    </AppLayout>
  );
}
