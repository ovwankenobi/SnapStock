import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { getCatalogSeller } from "../../api/catalog";
import AppLayout from "../../components/AppLayout";
import Avatar from "../../components/Avatar";
import EmptyState from "../../components/EmptyState";
import IconButton from "../../components/IconButton";
import { buyerNavItems } from "../../lib/nav";
import styles from "./buyer.module.css";
import { toFeedListing } from "./buyerFormat";
import ProductFeedCard from "./ProductFeedCard";

const BUSINESS_TYPE_LABELS = { wholesale: "Wholesale", retail: "Retail", both: "Wholesale & Retail" };

export default function SellerPage() {
  const { sellerId } = useParams();
  const navigate = useNavigate();

  const { data: seller, isLoading, isError } = useQuery({
    queryKey: ["catalogSeller", sellerId],
    queryFn: () => getCatalogSeller(sellerId),
  });

  return (
    <AppLayout
      navItems={buyerNavItems()}
      title="Seller"
      headerAction={<IconButton icon="back" label="Back" onClick={() => navigate(-1)} />}
    >
      <div className={styles.page}>
        {isLoading && <p className={styles.hint}>Loading seller...</p>}
        {isError && <EmptyState message="Could not load this seller." />}

        {seller && (
          <>
            <div className={styles["seller-header"]}>
              <Avatar name={seller.businessName} size="lg" />
              <div>
                <div className={styles["seller-header-name"]}>{seller.businessName}</div>
                <div className={styles["seller-header-meta"]}>
                  {BUSINESS_TYPE_LABELS[seller.businessType] || seller.businessType}
                  {seller.address ? ` · ${seller.address}` : ""}
                </div>
                {seller.description && (
                  <div className={styles["seller-header-description"]}>{seller.description}</div>
                )}
              </div>
            </div>

            {seller.products.length === 0 ? (
              <EmptyState message="This seller has no active listings right now." />
            ) : (
              <div className={styles.grid}>
                {seller.products.map((product) => (
                  <ProductFeedCard
                    key={product.id}
                    listing={toFeedListing(product)}
                    onOpen={() => navigate(`/buyer/products/${product.id}`)}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </AppLayout>
  );
}
