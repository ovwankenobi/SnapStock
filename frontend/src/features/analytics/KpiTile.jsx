import { deltaInfo } from "./analyticsFormat";
import styles from "./analytics.module.css";

// A headline number with its change against the previous period. The change carries a
// sign and a word ("vs previous"), so its meaning never depends on the color alone.
export default function KpiTile({ label, value, changePct, upIsGood = true, comparisonLabel }) {
  const delta = deltaInfo(changePct, { upIsGood });
  return (
    <div className={styles.kpi}>
      <div className={styles["kpi-label"]}>{label}</div>
      <div className={styles["kpi-value"]}>{value}</div>
      <div className={styles["kpi-delta"]}>
        {delta ? (
          <>
            <span className={`${styles["kpi-delta-value"]} ${styles[`delta-${delta.tone}`]}`}>{delta.label}</span>
            <span>{comparisonLabel}</span>
          </>
        ) : (
          <span>—</span>
        )}
      </div>
    </div>
  );
}
