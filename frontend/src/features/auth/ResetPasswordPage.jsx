import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { resetPassword } from "../../api/auth";
import { useAuth } from "./AuthContext";
import styles from "./auth.module.css";
import Icon from "../../components/Icon";
import Logo from "../../components/Logo";
import LanguageToggle from "./LanguageToggle";

const MIN_PASSWORD_LENGTH = 8;

export default function ResetPasswordPage() {
  const { t } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLinkInvalid, setIsLinkInvalid] = useState(!token);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(t("auth.reset.tooShort"));
      return;
    }
    if (password !== confirmPassword) {
      setError(t("auth.reset.mismatch"));
      return;
    }
    setIsSubmitting(true);
    try {
      await resetPassword(token, password);
      navigate("/login", { replace: true, state: { passwordReset: true } });
    } catch (err) {
      if (err.response?.status === 400) {
        setIsLinkInvalid(true);
      } else if (err.response?.status === 429) {
        setError(t("auth.forgot.tooMany"));
      } else {
        setError(t("auth.reset.error"));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.screen}>
      <LanguageToggle className={styles["language-toggle"]} />
      <Logo height={72} className={styles.logo} />

      {isLinkInvalid ? (
        <div className={styles["auth-form"]}>
          <div className={styles["form-error"]} role="alert">
            {t("auth.reset.invalidLink")}
          </div>
          <Link to="/forgot-password" className={`${styles["submit-button"]} ${styles["link-button"]}`}>
            {t("auth.reset.requestNew")}
          </Link>
        </div>
      ) : (
        <form className={styles["auth-form"]} onSubmit={handleSubmit}>
          <h1 className={styles["form-title"]}>{t("auth.reset.title")}</h1>
          <div>
            <label className={styles["field-label"]} htmlFor="reset-password">
              {t("auth.reset.newPassword")}
            </label>
            <div className={styles["password-field"]}>
              <input
                id="reset-password"
                className={styles["text-input"]}
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                enterKeyHint="next"
                minLength={MIN_PASSWORD_LENGTH}
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              <button
                type="button"
                className={styles["password-toggle"]}
                onClick={() => setShowPassword((shown) => !shown)}
                aria-label={showPassword ? t("auth.login.hidePassword") : t("auth.login.showPassword")}
                aria-pressed={showPassword}
              >
                <Icon name={showPassword ? "eyeOff" : "eye"} size={20} />
              </button>
            </div>
          </div>
          <div>
            <label className={styles["field-label"]} htmlFor="reset-confirm-password">
              {t("auth.reset.confirmPassword")}
            </label>
            <input
              id="reset-confirm-password"
              className={styles["text-input"]}
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              enterKeyHint="go"
              required
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
            />
          </div>

          {error && (
            <div className={styles["form-error"]} role="alert">
              {error}
            </div>
          )}

          <button type="submit" className={styles["submit-button"]} disabled={isSubmitting}>
            {isSubmitting ? t("auth.reset.submitting") : t("auth.reset.submit")}
          </button>
        </form>
      )}

      <p className={styles["switch-link"]}>
        <Link to="/login">{t("auth.forgot.backToLogin")}</Link>
      </p>
    </div>
  );
}
