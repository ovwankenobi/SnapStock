import { useState } from "react";
import { Link } from "react-router-dom";

import { requestPasswordReset } from "../../api/auth";
import { useAuth } from "./AuthContext";
import styles from "./auth.module.css";
import Logo from "../../components/Logo";
import LanguageToggle from "./LanguageToggle";

export default function ForgotPasswordPage() {
  const { t } = useAuth();
  const [email, setEmail] = useState("");
  const [isSent, setIsSent] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await requestPasswordReset(email);
      setIsSent(true);
    } catch (err) {
      setError(err.response?.status === 429 ? t("auth.forgot.tooMany") : t("auth.forgot.error"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.screen}>
      <LanguageToggle className={styles["language-toggle"]} />
      <Logo height={72} className={styles.logo} />

      <form className={styles["auth-form"]} onSubmit={handleSubmit}>
        <h1 className={styles["form-title"]}>{t("auth.forgot.title")}</h1>

        {isSent ? (
          <div className={styles["form-success"]} role="status">
            {t("auth.forgot.sent")}
          </div>
        ) : (
          <>
            <p className={styles["form-intro"]}>{t("auth.forgot.intro")}</p>
            <div>
              <label className={styles["field-label"]} htmlFor="forgot-email">
                {t("auth.forgot.email")}
              </label>
              <input
                id="forgot-email"
                className={styles["text-input"]}
                type="email"
                inputMode="email"
                autoComplete="email"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                enterKeyHint="send"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>

            {error && (
              <div className={styles["form-error"]} role="alert">
                {error}
              </div>
            )}

            <button type="submit" className={styles["submit-button"]} disabled={isSubmitting}>
              {isSubmitting ? t("auth.forgot.submitting") : t("auth.forgot.submit")}
            </button>
          </>
        )}
      </form>

      <p className={styles["switch-link"]}>
        <Link to="/login">{t("auth.forgot.backToLogin")}</Link>
      </p>
    </div>
  );
}
