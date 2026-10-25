import { useEffect, useRef, useState } from "react";
import QrScanner from "qr-scanner";

import Sheet from "../../components/Sheet";
import { useAuth } from "./AuthContext";
import styles from "./auth.module.css";

const LOGIN_QR_PREFIX = "ssqr1_";

// Scans a login QR (made on the Profile page) with the camera, or reads it from an uploaded
// picture. Browsers only allow the camera on HTTPS or localhost, so the upload also covers
// phones on the LAN dev server and computers without a camera.
export default function QrScanSheet({ onClose, onKey }) {
  const { t } = useAuth();
  const videoRef = useRef(null);
  const scannerRef = useRef(null);
  const busyRef = useRef(false);
  const fileInputRef = useRef(null);
  const [cameraOk, setCameraOk] = useState(() => Boolean(window.isSecureContext && navigator.mediaDevices));
  const [error, setError] = useState(() =>
    window.isSecureContext && navigator.mediaDevices ? "" : t("auth.qr.noCamera"),
  );
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  useEffect(() => {
    if (!cameraOk || !videoRef.current) return undefined;
    const scanner = new QrScanner(videoRef.current, (result) => handleResult(result.data), {
      preferredCamera: "environment",
      highlightScanRegion: true,
      returnDetailedScanResult: true,
    });
    scannerRef.current = scanner;
    scanner.start().catch(() => {
      setCameraOk(false);
      setError(t("auth.qr.noCamera"));
    });
    return () => {
      scanner.destroy();
      scannerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cameraOk]);

  async function handleResult(data) {
    if (busyRef.current) return;
    if (!data?.startsWith(LOGIN_QR_PREFIX)) {
      setError(t("auth.qr.notLoginQr"));
      return;
    }
    busyRef.current = true;
    scannerRef.current?.stop();
    setError("");
    setIsLoggingIn(true);
    try {
      await onKey(data);
    } catch (err) {
      const status = err.response?.status;
      setError(status === 401 ? t("auth.qr.invalid") : status === 429 ? t("auth.qr.tooMany") : t("auth.qr.error"));
      setIsLoggingIn(false);
      busyRef.current = false;
      scannerRef.current?.start().catch(() => {});
    }
  }

  async function handleFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try {
      const result = await QrScanner.scanImage(file, { returnDetailedScanResult: true });
      await handleResult(result.data);
    } catch {
      setError(t("auth.qr.noQrInImage"));
    }
  }

  return (
    <Sheet onClose={onClose} label={t("auth.qr.scanTitle")}>
      <h2 className={styles["qr-sheet-title"]}>{t("auth.qr.scanTitle")}</h2>
      <p className={styles["change-password-hint"]}>{t("auth.qr.scanHint")}</p>

      {cameraOk && (
        <div className={styles["qr-video-wrap"]}>
          <video ref={videoRef} className={styles["qr-video"]} muted playsInline />
        </div>
      )}

      {isLoggingIn && (
        <div className={styles["form-success"]} role="status">
          {t("auth.qr.loggingIn")}
        </div>
      )}
      {error && (
        <div className={styles["form-error"]} role="alert">
          {error}
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className={styles["visually-hidden"]}
        onChange={handleFile}
        tabIndex={-1}
      />
      <button
        type="button"
        className={styles["submit-button"]}
        onClick={() => fileInputRef.current?.click()}
        disabled={isLoggingIn}
      >
        {t("auth.qr.uploadImage")}
      </button>
      <button type="button" className={styles["profile-account-row"]} onClick={onClose}>
        {t("auth.qr.cancel")}
      </button>
    </Sheet>
  );
}
