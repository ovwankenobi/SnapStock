import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "./AuthContext";
import styles from "./auth.module.css";
import Icon from "../../components/Icon";
import Logo from "../../components/Logo";
import LanguageToggle from "./LanguageToggle";
import QrScanSheet from "./QrScanSheet";

export default function LoginPage() {
  const { login, loginWithQr, t } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isScanning, setIsScanning] = useState(false);

  function goHome(user) {
    const redirectTo = location.state?.from?.pathname || (user.role === "seller" ? "/dashboard" : "/buyer");
    navigate(redirectTo, { replace: true });
  }

  async function handleQrKey(key) {
    goHome(await loginWithQr(key));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      goHome(await login(email, password));
    } catch {
      setError(t("auth.login.error"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.screen}>
      <LanguageToggle className={styles["language-toggle"]} />
      <Logo height={72} className={styles.logo} />

      <form className={styles["auth-form"]} onSubmit={handleSubmit}>
        <div>
          <label className={styles["field-label"]} htmlFor="login-email">
            {t("auth.login.email")}
          </label>
          <input
            id="login-email"
            className={styles["text-input"]}
            type="email"
            inputMode="email"
            autoComplete="email"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            enterKeyHint="next"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div>
          <label className={styles["field-label"]} htmlFor="login-password">
            {t("auth.login.password")}
          </label>
          <div className={styles["password-field"]}>
            <input
              id="login-password"
              className={styles["text-input"]}
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              enterKeyHint="go"
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
        <Link to="/forgot-password" className={styles["forgot-link"]}>
          {t("auth.login.forgotPassword")}
        </Link>

        {location.state?.passwordReset && !error && (
          <div className={styles["form-success"]} role="status">
            {t("auth.login.resetSuccess")}
          </div>
        )}

        {error && (
          <div className={styles["form-error"]} role="alert">
            {error}
          </div>
        )}

        <button type="submit" className={styles["submit-button"]} disabled={isSubmitting}>
          {isSubmitting ? t("auth.login.submitting") : t("auth.login.submit")}
        </button>
        <button
          type="button"
          className={`${styles["profile-account-row"]} ${styles["qr-login-button"]}`}
          onClick={() => setIsScanning(true)}
        >
          {t("auth.login.withQr")}
        </button>
      </form>

      {isScanning && <QrScanSheet onClose={() => setIsScanning(false)} onKey={handleQrKey} />}

      <p className={styles["switch-link"]}>
        {t("auth.login.noAccount")} <Link to="/register">{t("auth.login.createAccount")}</Link>
      </p>
    </div>
  );
}
