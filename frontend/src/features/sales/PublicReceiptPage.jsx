import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { getPublicReceipt } from "../../api/sales";
import ReceiptCard from "./ReceiptCard";
import { publicReceiptToReceipt } from "./salesFormat";
import styles from "./sales.module.css";

export default function PublicReceiptPage() {
  const { receiptCode } = useParams();

  const { data: receipt, isLoading, isError } = useQuery({
    queryKey: ["publicReceipt", receiptCode],
    queryFn: () => getPublicReceipt(receiptCode),
    retry: false,
  });

  return (
    <div className={styles["public-page"]}>
      <div className={styles["receipt-screen"]}>
        {isLoading && <p className={styles["public-not-found"]}>Loading receipt...</p>}
        {isError && <p className={styles["public-not-found"]}>This receipt could not be found.</p>}
        {receipt && <ReceiptCard receipt={publicReceiptToReceipt(receipt)} />}
      </div>
    </div>
  );
}
