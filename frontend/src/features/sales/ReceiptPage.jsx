import { useQuery } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { useNavigate, useParams } from "react-router-dom";

import { getSale } from "../../api/sales";
import AppLayout from "../../components/AppLayout";
import { useAuth } from "../auth/AuthContext";
import { sellerNavItems } from "../../lib/nav";
import ReceiptCard from "./ReceiptCard";
import { saleToReceipt } from "./salesFormat";
import styles from "./sales.module.css";

export default function ReceiptPage() {
  const { saleId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const { data: sale, isLoading, isError } = useQuery({
    queryKey: ["sale", saleId],
    queryFn: () => getSale(saleId),
  });

  const publicUrl = sale ? `${window.location.origin}/r/${sale.receiptCode}` : "";

  function handleShare() {
    if (navigator.share) {
      navigator.share({ title: "Receipt", url: publicUrl }).catch(() => {});
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(publicUrl);
    }
  }

  return (
    <AppLayout navItems={sellerNavItems()} title="Receipt">
      <div className={styles["receipt-screen"]}>
        {isLoading && <p className={styles.hint}>Loading receipt...</p>}
        {isError && <p className={styles.hint}>Could not load this receipt.</p>}
        {sale && (
          <>
            <div className={styles["receipt-check"]}>✓</div>
            <div className={styles["receipt-thanks"]}>Thank you for your purchase!</div>
            <div className={styles["receipt-subtitle"]}>{sale.receiptCode}</div>

            <div className={`${styles["qr-wrap"]} no-print`}>
              <QRCodeSVG value={publicUrl} size={144} />
            </div>
            <div className={`${styles["qr-link"]} no-print`}>{publicUrl}</div>

            <ReceiptCard
              receipt={saleToReceipt(sale, { shopName: user?.sellerProfile?.businessName, servedBy: user?.fullName })}
            />

            <div className={`${styles["receipt-actions"]} no-print`}>
              <button type="button" className={styles["receipt-action-button"]} onClick={handleShare}>
                Share
              </button>
              <button type="button" className={styles["receipt-action-button"]} onClick={() => window.print()}>
                Print
              </button>
            </div>
            <button
              type="button"
              className={`${styles["receipt-home-button"]} no-print`}
              onClick={() => navigate("/sales")}
            >
              New Sale
            </button>
          </>
        )}
      </div>
    </AppLayout>
  );
}
