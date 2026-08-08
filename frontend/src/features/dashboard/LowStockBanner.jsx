import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { getLowStockProducts } from "../../api/products";
import Icon from "../../components/Icon";
import styles from "./dashboard.module.css";

export default function LowStockBanner() {
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState(false);

  const { data } = useQuery({ queryKey: ["lowStockProducts"], queryFn: getLowStockProducts });

  if (dismissed || !data || data.length === 0) return null;

  return (
    <div className={styles["low-stock-banner"]}>
      <button
        type="button"
        className={styles["low-stock-banner-body"]}
        onClick={() => navigate("/inventory")}
      >
        <Icon name="warning" size={16} color="var(--color-warning)" />
        <span>
          <strong>{data.length}</strong> product{data.length === 1 ? "" : "s"}{" "}
          {data.length === 1 ? "needs" : "need"} restocking:{" "}
          {data.map((product) => product.name).join(", ")}
        </span>
      </button>
      <button
        type="button"
        className={styles["low-stock-banner-dismiss"]}
        onClick={() => setDismissed(true)}
        aria-label="Dismiss"
      >
        <Icon name="close" size={14} />
      </button>
    </div>
  );
}
