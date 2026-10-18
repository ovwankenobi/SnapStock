import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getInsights } from "../../api/analytics";
import Badge from "../../components/Badge";
import Icon from "../../components/Icon";
import { useAuth } from "../auth/AuthContext";
import styles from "./analytics.module.css";
import { SEVERITY_TONE, insightAction, insightBody, insightTitle } from "./insightText";

const COLLAPSED_COUNT = 3;

// The most important rule-based findings, each with the figures behind it and a next step.
export default function InsightsFeed() {
  const { t } = useAuth();
  const [isOpen, setIsOpen] = useState(true);
  const [showAll, setShowAll] = useState(false);
  const { data } = useQuery({ queryKey: ["analyticsInsights"], queryFn: getInsights });

  if (!data || data.length === 0) return null;
  const visible = showAll ? data : data.slice(0, COLLAPSED_COUNT);
  const highCount = data.filter((insight) => insight.severity === "high").length;

  return (
    <div className={`${styles.card} ${styles.insights}`}>
      <button
        type="button"
        className={styles["insights-toggle"]}
        onClick={() => setIsOpen((open) => !open)}
        aria-expanded={isOpen}
      >
        <span className={styles["insights-title"]}>{t("insights.heading")}</span>
        {highCount > 0 && <Badge tone="danger">{t("insights.urgent", { count: highCount })}</Badge>}
        <span aria-hidden="true" style={{ display: "flex", transform: isOpen ? "rotate(180deg)" : undefined }}>
          <Icon name="chevron" size={16} />
        </span>
      </button>
      {isOpen && (
        <>
          {visible.map((insight, index) => (
            <div key={`${insight.code}-${insight.productId || index}`} className={styles.insight}>
              <div className={styles["insight-top"]}>
                <Badge tone={SEVERITY_TONE[insight.severity]}>{t(`insights.severity.${insight.severity}`)}</Badge>
                <span className={styles["insight-title"]}>{insightTitle(t, insight)}</span>
              </div>
              <div className={styles["insight-body"]}>{insightBody(t, insight)}</div>
              <div className={styles["insight-action"]}>→ {insightAction(t, insight)}</div>
            </div>
          ))}
          {data.length > COLLAPSED_COUNT && (
            <button type="button" className={styles["insights-more"]} onClick={() => setShowAll((all) => !all)}>
              {showAll ? t("insights.showFewer") : t("insights.showAll", { count: data.length })}
            </button>
          )}
        </>
      )}
    </div>
  );
}
