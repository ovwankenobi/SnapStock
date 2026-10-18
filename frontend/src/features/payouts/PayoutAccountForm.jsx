import { useEffect, useState } from "react";

import Icon from "../../components/Icon";
import SegmentedControl from "../../components/SegmentedControl";
import { mediaUrl } from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import { emptyPayoutDraft, needsBankName, PAYOUT_METHODS, payoutMethodLabel } from "./payoutFormat";
import styles from "./payouts.module.css";

export default function PayoutAccountForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel,
  cancelLabel,
  isSubmitting = false,
  error,
}) {
  const { t } = useAuth();
  const [draft, setDraft] = useState(() => initial || emptyPayoutDraft());
  const [qrFile, setQrFile] = useState(null);
  const [qrPreview, setQrPreview] = useState(null);

  useEffect(() => {
    if (!qrFile) {
      setQrPreview(null);
      return undefined;
    }
    const url = URL.createObjectURL(qrFile);
    setQrPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [qrFile]);

  function updateField(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  const methodOptions = PAYOUT_METHODS.map((method) => ({ value: method, label: payoutMethodLabel(t, method) }));
  const shownQr = qrPreview || mediaUrl(draft.qrUrl);

  return (
    <form
      className={styles.form}
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(draft, qrFile);
      }}
    >
      <div>
        <div className={styles["field-label"]}>{t("payouts.method")}</div>
        <SegmentedControl options={methodOptions} value={draft.method} onChange={(value) => updateField("method", value)} />
      </div>

      {needsBankName(draft.method) && (
        <div>
          <label className={styles["field-label"]} htmlFor="payout-bankName">
            {draft.method === "bank_transfer" ? t("payouts.bankName") : t("payouts.providerName")}
          </label>
          <input
            id="payout-bankName"
            className={styles["text-input"]}
            required
            value={draft.bankName}
            onChange={(event) => updateField("bankName", event.target.value)}
          />
        </div>
      )}

      <div>
        <label className={styles["field-label"]} htmlFor="payout-accountName">
          {t("payouts.accountName")}
        </label>
        <input
          id="payout-accountName"
          className={styles["text-input"]}
          required
          value={draft.accountName}
          onChange={(event) => updateField("accountName", event.target.value)}
        />
      </div>

      <div>
        <label className={styles["field-label"]} htmlFor="payout-accountNumber">
          {t("payouts.accountNumber")}
        </label>
        <input
          id="payout-accountNumber"
          className={styles["text-input"]}
          required
          inputMode={needsBankName(draft.method) ? "text" : "tel"}
          value={draft.accountNumber}
          onChange={(event) => updateField("accountNumber", event.target.value)}
        />
      </div>

      <div>
        <div className={styles["field-label"]}>{t("payouts.qrCode")}</div>
        <label className={styles["qr-drop"]}>
          {shownQr ? (
            <>
              <img src={shownQr} alt={t("payouts.qrCode")} />
              <span>{t("payouts.qrChange")}</span>
            </>
          ) : (
            <>
              <Icon name="camera" size={28} />
              <span>{t("payouts.qrAdd")}</span>
            </>
          )}
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            hidden
            onChange={(event) => event.target.files[0] && setQrFile(event.target.files[0])}
          />
        </label>
      </div>

      {error && (
        <div className={styles.error} role="alert">
          {error}
        </div>
      )}

      <div className={styles.actions}>
        {onCancel && (
          <button type="button" className={styles.secondary} onClick={onCancel} disabled={isSubmitting}>
            {cancelLabel || t("payouts.cancel")}
          </button>
        )}
        <button type="submit" className={styles.primary} disabled={isSubmitting}>
          {isSubmitting ? t("payouts.saving") : submitLabel || t("payouts.save")}
        </button>
      </div>
    </form>
  );
}
