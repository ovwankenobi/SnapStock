import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { listCatalogProducts, searchCatalogByImage } from "../../api/catalog";
import AppLayout from "../../components/AppLayout";
import EmptyState from "../../components/EmptyState";
import IconButton from "../../components/IconButton";
import ImageSearchPanel from "../../components/ImageSearchPanel";
import LoadingState from "../../components/LoadingState";
import SearchField from "../../components/SearchField";
import { buyerNavItems } from "../../lib/nav";
import styles from "./buyer.module.css";
import { toFeedListing } from "./buyerFormat";
import ProductFeedCard from "./ProductFeedCard";

export default function BuyerHomePage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [showImageSearch, setShowImageSearch] = useState(false);
  const [imageSearch, setImageSearch] = useState(null); // { query, products }
  const [imageSearchError, setImageSearchError] = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["catalogProducts", { search: query, category }],
    queryFn: () => listCatalogProducts({ search: query, category, pageSize: 60 }),
    enabled: !imageSearch,
  });

  const products = imageSearch ? imageSearch.products : data?.items || [];
  const categories = useMemo(
    () => Array.from(new Set((data?.items || []).map((p) => p.category).filter(Boolean))).sort(),
    [data],
  );

  const imageSearchMutation = useMutation({
    mutationFn: searchCatalogByImage,
    onSuccess: (result) => {
      setImageSearch({ query: result.query, products: result.results.map((r) => r.product) });
      setShowImageSearch(false);
      setImageSearchError("");
    },
    onError: (err) => {
      setImageSearchError(err.response?.data?.detail || "Could not search by photo. Try again.");
    },
  });

  return (
    <AppLayout navItems={buyerNavItems()} title="Discover">
      <div className={styles.page}>
        <div className={styles.toolbar}>
          <SearchField
            value={query}
            onChange={(value) => {
              setQuery(value);
              setImageSearch(null);
            }}
            placeholder="Search sellers or products"
          />
          <IconButton icon="camera" label="Search by photo" onClick={() => setShowImageSearch(true)} />
        </div>

        {showImageSearch && (
          <ImageSearchPanel
            isSubmitting={imageSearchMutation.isPending}
            error={imageSearchError}
            onClose={() => setShowImageSearch(false)}
            onSubmit={(file, text) => {
              setImageSearchError("");
              imageSearchMutation.mutate({ file, query: text });
            }}
          />
        )}

        {imageSearch ? (
          <div className={styles["active-filter"]}>
            <span>Photo search: "{imageSearch.query}"</span>
            <button type="button" onClick={() => setImageSearch(null)}>
              Clear
            </button>
          </div>
        ) : (
          categories.length > 0 && (
            <div className={styles.chips}>
              <button
                type="button"
                className={`${styles.chip} ${category === "" ? styles["chip-active"] : ""}`}
                onClick={() => setCategory("")}
              >
                All
              </button>
              {categories.map((cat) => (
                <button
                  key={cat}
                  type="button"
                  className={`${styles.chip} ${category === cat ? styles["chip-active"] : ""}`}
                  onClick={() => setCategory(cat === category ? "" : cat)}
                >
                  {cat}
                </button>
              ))}
            </div>
          )
        )}

        {!imageSearch && isLoading && <LoadingState message="Loading products…" />}
        {!imageSearch && isError && <EmptyState message="Could not load products." />}
        {!isLoading && products.length === 0 && (
          <EmptyState message={imageSearch ? "No matches for that photo search." : "No products found."} />
        )}

        <div className={styles.grid}>
          {products.map((product) => (
            <ProductFeedCard
              key={product.id}
              listing={toFeedListing(product)}
              onOpen={() => navigate(`/buyer/products/${product.id}`)}
            />
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
