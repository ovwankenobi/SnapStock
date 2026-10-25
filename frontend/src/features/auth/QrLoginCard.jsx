import { useRef, useState } from "react";
import { QRCodeCanvas } from "qrcode.react";

import { createQrLoginKey, revokeQrLoginKey } from "../../api/auth";
import Sheet from "../../components/Sheet";
import { useAuth } from "./AuthContext";
import styles from "./auth.module.css";

// The login QR is scanned on the login page instead of typing an email and password. The server
// only keeps a hash of it, so the QR is shown once (to download) right after it is made.
export default function QrLoginCard() {
  const { user, language, refreshUser, t } = useAuth();
  const canvasRef = useRef(null);
  const [step, setStep] = useState(null); // null | "password" | "show"
  const [password, setPassword] = useState("");
  const [key, setKey] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const activeSince = user.qrLoginCreatedAt
    ? new Date(user.qrLoginCreatedAt).toLocaleDateString(language === "tl" ? "fil-PH" : "en-PH", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : null;

  function openPasswordStep() {
    setPassword("");
    setError("");
    setStep("password");
  }

  function close() {
    setStep(null);
    setKey("");
    setPassword("");
  }

  async function handleCreate(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      const data = await createQrLoginKey(password);
      setKey(data.key);
      setStep("show");
      refreshUser().catch(() => {});
    } catch (err) {
      const status = err.response?.status;
      setError(status === 400 ? t("auth.qr.wrongPassword") : status === 429 ? t("auth.qr.tooMany") : t("auth.qr.createError"));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRevoke() {
    if (!window.confirm(t("auth.qr.revokeConfirm"))) return;
    try {
      await revokeQrLoginKey();
      await refreshUser();
    } catch {
      // the row keeps showing "active", so the seller can try again
    }
  }

  function handleDownload() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement("a");
    link.href = canvas.toDataURL("image/png");
    link.download = "snapstock-login-qr.png";
    link.click();
  }

  return (
    <section className={styles["change-password"]}>
      <div className={styles["field-label"]}>{t("auth.qr.title")}</div>
      <p className={styles["change-password-hint"]}>
        {activeSince ? t("auth.qr.activeSince", { date: activeSince }) : t("auth.qr.hint")}
      </p>

      <button type="button" className={styles["profile-account-row"]} onClick={openPasswordStep}>
        {activeSince ? t("auth.qr.regenerate") : t("auth.qr.create")}
      </button>
      {activeSince && (
        <button
          type="button"
          className={`${styles["profile-account-row"]} ${styles["profile-logout"]}`}
          onClick={handleRevoke}
        >
          {t("auth.qr.revoke")}
        </button>
      )}

      {step === "password" && (
        <Sheet onClose={close} label={t("auth.qr.title")}>
          <h2 className={styles["qr-sheet-title"]}>{activeSince ? t("auth.qr.regenerate") : t("auth.qr.create")}</h2>
          <form className={styles["qr-form"]} onSubmit={handleCreate}>
            <p className={styles["change-password-hint"]}>{t("auth.qr.passwordPrompt")}</p>
            <div>
              <label className={styles["field-label"]} htmlFor="qr-password">
                {t("auth.qr.password")}
              </label>
              <input
                id="qr-password"
                className={styles["text-input"]}
                type="password"
                autoComplete="current-password"
                autoFocus
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
              {isSubmitting ? t("auth.qr.submitting") : t("auth.qr.submit")}
            </button>
          </form>
        </Sheet>
      )}

      {step === "show" && (
        <Sheet onClose={close} centered label={t("auth.qr.title")}>
          <h2 className={styles["qr-sheet-title"]}>{t("auth.qr.title")}</h2>
          <div className={styles["qr-code-box"]}>
            <QRCodeCanvas ref={canvasRef} value={key} size={240} marginSize={2} level="M" />
          </div>
          <div className={styles["form-error"]} role="note">
            {t("auth.qr.warning")}
          </div>
          <button type="button" className={`${styles["submit-button"]} ${styles["qr-full"]}`} onClick={handleDownload}>
            {t("auth.qr.download")}
          </button>
          <button type="button" className={`${styles["profile-account-row"]} ${styles["qr-full"]}`} onClick={close}>
            {t("auth.qr.done")}
          </button>
        </Sheet>
      )}
    </section>
  );
}
