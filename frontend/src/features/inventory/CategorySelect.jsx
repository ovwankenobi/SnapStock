import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { deleteProductCategory, getProductCategories } from "../../api/products";
import Icon from "../../components/Icon";
import styles from "./inventory.module.css";

export default function CategorySelect({ value, onChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const rootRef = useRef(null);
  const searchRef = useRef(null);
  const queryClient = useQueryClient();

  // Under the "products" key so saving a product (which invalidates ["products"]) refreshes this list too.
  const { data: savedCategories = [] } = useQuery({
    queryKey: ["products", "categories"],
    queryFn: getProductCategories,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProductCategory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["products"] }),
  });

  // Keep the current value selectable even if it's new and not saved on any product yet.
  const categories = useMemo(() => {
    const all = [...savedCategories];
    if (value && !all.some((c) => c.toLowerCase() === value.toLowerCase())) all.unshift(value);
    return all;
  }, [savedCategories, value]);

  const term = search.trim();
  const filtered = categories.filter((c) => c.toLowerCase().includes(term.toLowerCase()));
  const exactMatch = categories.find((c) => c.toLowerCase() === term.toLowerCase());

  useEffect(() => {
    if (!isOpen) return undefined;
    function handlePointerDown(e) {
      if (rootRef.current && !rootRef.current.contains(e.target)) close();
    }
    document.addEventListener("pointerdown", handlePointerDown);
    searchRef.current?.focus();
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [isOpen]);

  function close() {
    setIsOpen(false);
    setSearch("");
    setIsAdding(false);
  }

  function select(category) {
    onChange(category);
    close();
  }

  function handleDelete(category) {
    const isSaved = savedCategories.includes(category);
    if (
      isSaved &&
      !window.confirm(`Delete category "${category}"? It will be removed from every product that uses it.`)
    ) {
      return;
    }
    if (category === value) onChange("");
    if (isSaved) deleteMutation.mutate(category);
    searchRef.current?.focus();
  }

  function handleAddNew() {
    if (!term) {
      setIsAdding(true);
      searchRef.current?.focus();
      return;
    }
    select(exactMatch || term);
  }

  function handleKeyDown(e) {
    if (e.key === "Escape") {
      e.preventDefault();
      close();
    } else if (e.key === "Enter") {
      // Never let Enter here submit the product form.
      e.preventDefault();
      if (term) select(exactMatch || term);
    }
  }

  return (
    <div className={styles["select-root"]} ref={rootRef}>
      <button
        type="button"
        className={`${styles["text-input"]} ${styles["select-trigger"]}`}
        onClick={() => (isOpen ? close() : setIsOpen(true))}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <span className={value ? "" : styles["select-placeholder"]}>{value || "Select category"}</span>
        <span className={`${styles["select-caret"]} ${isOpen ? styles["select-caret-open"] : ""}`}>▾</span>
      </button>

      {isOpen && (
        <div className={styles["select-panel"]}>
          <div className={styles["select-search"]}>
            <Icon name="search" size={16} />
            <input
              ref={searchRef}
              value={search}
              maxLength={60}
              placeholder={isAdding ? "Type new category name" : "Search categories"}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={handleKeyDown}
            />
          </div>

          <button type="button" className={`${styles["select-option"]} ${styles["select-add"]}`} onClick={handleAddNew}>
            <Icon name="plus" size={14} />
            {term && !exactMatch ? `Add "${term}"` : "Add new category"}
          </button>

          <ul className={styles["select-list"]} role="listbox">
            {value && !term && (
              <li>
                <button type="button" className={`${styles["select-option"]} ${styles["select-muted"]}`} onClick={() => select("")}>
                  No category
                </button>
              </li>
            )}
            {filtered.map((category) => (
              <li key={category} className={styles["select-row"]}>
                <button
                  type="button"
                  role="option"
                  aria-selected={category === value}
                  className={`${styles["select-option"]} ${category === value ? styles["select-option-active"] : ""}`}
                  onClick={() => select(category)}
                >
                  {category}
                  {category === value && <Icon name="check" size={14} />}
                </button>
                <button
                  type="button"
                  className={styles["select-delete"]}
                  onClick={() => handleDelete(category)}
                  disabled={deleteMutation.isPending && deleteMutation.variables === category}
                  aria-label={`Delete category ${category}`}
                  title="Delete category"
                >
                  <Icon name="close" size={14} />
                </button>
              </li>
            ))}
            {filtered.length === 0 && (
              <li className={styles["select-empty"]}>{term ? "No matching categories" : "No categories yet"}</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
