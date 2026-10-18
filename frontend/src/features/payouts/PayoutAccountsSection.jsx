import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deletePayoutAccount, savePayoutAccount, updatePayoutAccount } from "../../api/payouts";
import { useAuth } from "../auth/AuthContext";
import PayoutAccountCard from "./PayoutAccountCard";
import PayoutAccountForm from "./PayoutAccountForm";
import { draftFromAccount, payloadFromDraft } from "./payoutFormat";
import styles from "./payouts.module.css";

const NEW = "new";

export default function PayoutAccountsSection() {
  const { user, refreshUser, t } = useAuth();
  const queryClient = useQueryClient();
  const accounts = user.sellerProfile?.payoutAccounts || [];
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");

  async function afterChange() {
    await refreshUser();
    queryClient.invalidateQueries({ queryKey: ["catalogSeller", user.id] });
  }

  const saveMutation = useMutation({
    mutationFn: ({ id, draft, qrFile }) =>
      savePayoutAccount({ id, values: payloadFromDraft(draft), qrFile }),
    onSuccess: async () => {
      setEditingId(null);
      await afterChange();
    },
    onError: () => setError(t("payouts.saveError")),
  });

  const defaultMutation = useMutation({
    mutationFn: (id) => updatePayoutAccount(id, { isDefault: true }),
    onSuccess: afterChange,
  });

  const deleteMutation = useMutation({
    mutationFn: deletePayoutAccount,
    onSuccess: afterChange,
  });

  function startEditing(id) {
    setError("");
    setEditingId(id);
  }

  function handleDelete(id) {
    if (window.confirm(t("payouts.confirmDelete"))) deleteMutation.mutate(id);
  }

  function renderForm(account) {
    return (
      <PayoutAccountForm
        key={account?.id || NEW}
        initial={account ? draftFromAccount(account) : undefined}
        onSubmit={(draft, qrFile) => {
          setError("");
          saveMutation.mutate({ id: account?.id, draft, qrFile });
        }}
        onCancel={() => setEditingId(null)}
        isSubmitting={saveMutation.isPending}
        error={error}
      />
    );
  }

  return (
    <section className={styles.section}>
      <div className={styles["field-label"]}>{t("payouts.title")}</div>
      <p className={styles["section-hint"]}>{t("payouts.subtitle")}</p>

      {accounts.length === 0 && editingId !== NEW && <p className={styles["section-hint"]}>{t("payouts.empty")}</p>}

      {accounts.map((account) =>
        editingId === account.id ? (
          <div key={account.id}>{renderForm(account)}</div>
        ) : (
          <PayoutAccountCard key={account.id} account={account} showDefault>
            <div className={styles["card-actions"]}>
              {!account.isDefault && (
                <button
                  type="button"
                  className={styles["link-button"]}
                  onClick={() => defaultMutation.mutate(account.id)}
                >
                  {t("payouts.makeDefault")}
                </button>
              )}
              <button type="button" className={styles["link-button"]} onClick={() => startEditing(account.id)}>
                {t("payouts.edit")}
              </button>
              <button
                type="button"
                className={`${styles["link-button"]} ${styles["link-danger"]}`}
                onClick={() => handleDelete(account.id)}
              >
                {t("payouts.delete")}
              </button>
            </div>
          </PayoutAccountCard>
        ),
      )}

      {editingId === NEW ? (
        renderForm(null)
      ) : (
        <button type="button" className={styles["add-button"]} onClick={() => startEditing(NEW)}>
          + {t("payouts.add")}
        </button>
      )}
    </section>
  );
}
