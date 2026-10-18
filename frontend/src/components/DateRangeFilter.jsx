import { useState } from "react";

import { useAuth } from "../features/auth/AuthContext";
import { daysAgoInputValue, toDateInputValue } from "../lib/dates";
import SegmentedControl from "./SegmentedControl";
import styles from "./primitives.module.css";

export const RANGE_VALUES = ["today", "week", "month", "custom"];

// Range state shared by the date filter and the queries it drives.
// `period` is null while a custom range is incomplete or backwards.
export function useDateRange(initial = "week") {
  const [range, setRange] = useState(initial);
  const [start, setStart] = useState(() => daysAgoInputValue(6));
  const [end, setEnd] = useState(() => toDateInputValue(new Date()));
  const isCustom = range === "custom";
  const isValid = !isCustom || Boolean(start && end && start <= end);
  const period = !isValid ? null : isCustom ? { range, start, end } : { range };
  return { range, setRange, start, setStart, end, setEnd, isCustom, isValid, period };
}

export default function DateRangeFilter({ state }) {
  const { t } = useAuth();
  const today = toDateInputValue(new Date());
  const options = RANGE_VALUES.map((value) => ({ value, label: t(`dateRange.${value}`) }));

  return (
    <div className={styles["date-filter"]}>
      <SegmentedControl options={options} value={state.range} onChange={state.setRange} />
      {state.isCustom && (
        <div className={styles["date-range"]}>
          <label className={styles["date-range-field"]}>
            <span>{t("dateRange.from")}</span>
            <input
              type="date"
              value={state.start}
              max={state.end || today}
              onChange={(e) => state.setStart(e.target.value)}
            />
          </label>
          <label className={styles["date-range-field"]}>
            <span>{t("dateRange.to")}</span>
            <input
              type="date"
              value={state.end}
              min={state.start || undefined}
              max={today}
              onChange={(e) => state.setEnd(e.target.value)}
            />
          </label>
          {!state.isValid && <p className={styles["date-range-error"]}>{t("dateRange.invalid")}</p>}
        </div>
      )}
    </div>
  );
}
