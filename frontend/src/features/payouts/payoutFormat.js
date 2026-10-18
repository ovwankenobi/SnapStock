export const PAYOUT_METHODS = ["gcash", "maya", "bank_transfer", "other"];

const METHODS_NEEDING_BANK_NAME = new Set(["bank_transfer", "other"]);

export function needsBankName(method) {
  return METHODS_NEEDING_BANK_NAME.has(method);
}

export function payoutMethodLabel(t, method) {
  return t(`payouts.methods.${method}`);
}

// Card heading: "GCash", or the bank/provider name for bank and other accounts.
export function payoutAccountTitle(t, account) {
  return needsBankName(account.method) && account.bankName
    ? account.bankName
    : payoutMethodLabel(t, account.method);
}

export function emptyPayoutDraft() {
  return { method: "gcash", accountName: "", accountNumber: "", bankName: "", qrUrl: null };
}

export function draftFromAccount(account) {
  return {
    method: account.method,
    accountName: account.accountName,
    accountNumber: account.accountNumber,
    bankName: account.bankName || "",
    qrUrl: account.qrUrl,
  };
}

export function payloadFromDraft(draft) {
  return {
    method: draft.method,
    accountName: draft.accountName.trim(),
    accountNumber: draft.accountNumber.trim(),
    bankName: needsBankName(draft.method) ? draft.bankName.trim() : null,
  };
}
