import { useState } from "react";

import { requestPasswordChange } from "../../api/auth";
import { useAuth } from "./AuthContext";
import styles from "./auth.module.css";

// Changing a password works like "Forgot password": we email a link to the account's address
// and the new password is set on /reset-password.
export default function ChangePasswordSection() {
  const { user, t } = useAuth();
  const [isSent, setIsSent] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSend() {
    setError("");
    setIsSubmitting(true);
    try {
      await requestPasswordChange();
      setIsSent(true);
    } catch (err) {
      setError(err.response?.status === 429 ? t("auth.changePassword.tooMany") : t("auth.changePassword.error"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className={styles["change-password"]}>
      <div className={styles["field-label"]}>{t("auth.changePassword.title")}</div>

      {isSent ? (
        <div className={styles["form-success"]} role="status">
          {t("auth.changePassword.sent", { email: user.email })}
        </div>
      ) : (
        <p className={styles["change-password-hint"]}>{t("auth.changePassword.hint", { email: user.email })}</p>
      )}

      {error && (
        <div className={styles["form-error"]} role="alert">
          {error}
        </div>
      )}

      <button type="button" className={styles["profile-account-row"]} onClick={handleSend} disabled={isSubmitting}>
        {isSubmitting
          ? t("auth.changePassword.submitting")
          : isSent
            ? t("auth.changePassword.sendAgain")
            : t("auth.changePassword.submit")}
      </button>
    </section>
  );
}
