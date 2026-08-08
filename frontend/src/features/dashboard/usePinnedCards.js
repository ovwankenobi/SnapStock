import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "dashboard.pinnedCardIds";

export function usePinnedCards(allIds) {
  const [pinnedIds, setPinnedIds] = useState(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (Array.isArray(stored) && stored.every((id) => allIds.includes(id))) {
        return stored;
      }
    } catch {
      // malformed storage — fall back to the default set below
    }
    return allIds;
  });
  const [isCustomizing, setIsCustomizing] = useState(false);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(pinnedIds));
  }, [pinnedIds]);

  const togglePinned = useCallback((id) => {
    setPinnedIds((current) =>
      current.includes(id) ? current.filter((existing) => existing !== id) : [...current, id],
    );
  }, []);

  return { pinnedIds, togglePinned, isCustomizing, setIsCustomizing };
}
