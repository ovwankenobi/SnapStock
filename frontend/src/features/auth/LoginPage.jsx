import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "./AuthContext";
import styles from "./auth.module.css";
import LanguageToggle from "./LanguageToggle";

export default function LoginPage() {
  const { login, t } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      const user = await login(email, password);
      const redirectTo = location.state?.from?.pathname || (user.role === "seller" ? "/dashboard" : "/buyer");
      navigate(redirectTo, { replace: true });
    } catch {
      setError(t("auth.login.error"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.screen}>
      <LanguageToggle className={styles["language-toggle"]} />
      <div className={styles.mark}>S</div>
      <div className={styles["app-name"]}>{t("common.appName")}</div>
      <p className={styles.tagline}>{t("common.tagline")}</p>

      <form className={styles["auth-form"]} onSubmit={handleSubmit}>
        <div>
          <label className={styles["field-label"]} htmlFor="login-email">
            {t("auth.login.email")}
          </label>
          <input
            id="login-email"
            className={styles["text-input"]}
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div>
          <label className={styles["field-label"]} htmlFor="login-password">
            {t("auth.login.password")}
          </label>
          <input
            id="login-password"
            className={styles["text-input"]}
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>

        {error && (
          <div className={styles["form-error"]} role="alert">
            {error}
          </div>
        )}

        <button type="submit" className={styles["submit-button"]} disabled={isSubmitting}>
          {isSubmitting ? t("auth.login.submitting") : t("auth.login.submit")}
        </button>
      </form>

      <p className={styles["switch-link"]}>
        {t("auth.login.noAccount")} <Link to="/register">{t("auth.login.createAccount")}</Link>
      </p>
    </div>
  );
}
