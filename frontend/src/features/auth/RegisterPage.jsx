import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "./AuthContext";
import styles from "./auth.module.css";
import LanguageToggle from "./LanguageToggle";
import RoleOptionCard from "./RoleOptionCard";

const BUSINESS_TYPE_LABEL_KEYS = {
  retail: "auth.register.businessTypeRetail",
  wholesale: "auth.register.businessTypeWholesale",
  both: "auth.register.businessTypeBoth",
};

const INITIAL_FORM = {
  fullName: "",
  email: "",
  password: "",
  phone: "",
  businessName: "",
  businessType: "retail",
  address: "",
  description: "",
};

export default function RegisterPage() {
  const { register, t } = useAuth();
  const navigate = useNavigate();
  const [role, setRole] = useState(null);
  const [form, setForm] = useState(INITIAL_FORM);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      const payload = {
        email: form.email,
        password: form.password,
        fullName: form.fullName,
        role,
        phone: form.phone || undefined,
        ...(role === "seller"
          ? {
              businessName: form.businessName,
              businessType: form.businessType,
              address: form.address || undefined,
              description: form.description || undefined,
            }
          : {}),
      };
      const user = await register(payload);
      navigate(user.role === "seller" ? "/dashboard" : "/buyer", { replace: true });
    } catch (err) {
      setError(err.response?.status === 400 ? t("auth.register.emailTaken") : t("auth.register.error"));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!role) {
    return (
      <div className={styles.screen}>
        <LanguageToggle className={styles["language-toggle"]} />
        <div className={styles.mark}>S</div>
        <div className={styles["app-name"]}>{t("common.appName")}</div>
        <p className={styles.tagline}>{t("auth.register.chooseRole")}</p>
        <div className={styles.roles}>
          <RoleOptionCard
            icon="box"
            title={t("roles.seller.title")}
            description={t("roles.seller.description")}
            primary
            onSelect={() => setRole("seller")}
          />
          <RoleOptionCard
            icon="user"
            title={t("roles.buyer.title")}
            description={t("roles.buyer.description")}
            onSelect={() => setRole("buyer")}
          />
        </div>
        <p className={styles["switch-link"]}>
          {t("auth.register.haveAccount")} <Link to="/login">{t("auth.register.signIn")}</Link>
        </p>
      </div>
    );
  }

  return (
    <div className={styles.screen}>
      <LanguageToggle className={styles["language-toggle"]} />
      <button type="button" className={styles["back-link"]} onClick={() => setRole(null)}>
        ← {t("auth.register.back")}
      </button>
      <div className={styles["app-name"]}>
        {role === "seller" ? t("auth.register.titleSeller") : t("auth.register.titleBuyer")}
      </div>

      <form className={styles["auth-form"]} onSubmit={handleSubmit}>
        <div>
          <label className={styles["field-label"]} htmlFor="reg-fullName">
            {t("auth.register.fullName")}
          </label>
          <input
            id="reg-fullName"
            className={styles["text-input"]}
            required
            value={form.fullName}
            onChange={(event) => updateField("fullName", event.target.value)}
          />
        </div>
        <div>
          <label className={styles["field-label"]} htmlFor="reg-email">
            {t("auth.register.email")}
          </label>
          <input
            id="reg-email"
            className={styles["text-input"]}
            type="email"
            autoComplete="email"
            required
            value={form.email}
            onChange={(event) => updateField("email", event.target.value)}
          />
        </div>
        <div>
          <label className={styles["field-label"]} htmlFor="reg-password">
            {t("auth.register.password")}
          </label>
          <input
            id="reg-password"
            className={styles["text-input"]}
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={form.password}
            onChange={(event) => updateField("password", event.target.value)}
          />
        </div>
        <div>
          <label className={styles["field-label"]} htmlFor="reg-phone">
            {t("auth.register.phone")}
          </label>
          <input
            id="reg-phone"
            className={styles["text-input"]}
            value={form.phone}
            onChange={(event) => updateField("phone", event.target.value)}
          />
        </div>

        {role === "seller" && (
          <>
            <div>
              <label className={styles["field-label"]} htmlFor="reg-businessName">
                {t("auth.register.businessName")}
              </label>
              <input
                id="reg-businessName"
                className={styles["text-input"]}
                required
                value={form.businessName}
                onChange={(event) => updateField("businessName", event.target.value)}
              />
            </div>
            <div>
              <div className={styles["field-label"]}>{t("auth.register.businessType")}</div>
              <div className={styles["chip-row"]}>
                {Object.keys(BUSINESS_TYPE_LABEL_KEYS).map((type) => (
                  <button
                    key={type}
                    type="button"
                    className={`${styles["type-toggle"]} ${form.businessType === type ? styles["type-toggle-active"] : ""}`}
                    onClick={() => updateField("businessType", type)}
                  >
                    {t(BUSINESS_TYPE_LABEL_KEYS[type])}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className={styles["field-label"]} htmlFor="reg-address">
                {t("auth.register.address")}
              </label>
              <input
                id="reg-address"
                className={styles["text-input"]}
                value={form.address}
                onChange={(event) => updateField("address", event.target.value)}
              />
            </div>
            <div>
              <label className={styles["field-label"]} htmlFor="reg-description">
                {t("auth.register.description")}
              </label>
              <textarea
                id="reg-description"
                className={styles.textarea}
                value={form.description}
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

        <button type="submit" className={styles["submit-button"]} disabled={isSubmitting}>
          {isSubmitting ? t("auth.register.submitting") : t("auth.register.submit")}
        </button>
      </form>

      <p className={styles["switch-link"]}>
        {t("auth.register.haveAccount")} <Link to="/login">{t("auth.register.signIn")}</Link>
      </p>
    </div>
  );
}
