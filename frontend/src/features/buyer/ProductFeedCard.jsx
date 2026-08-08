import Badge from "../../components/Badge";
import ProductThumb from "../../components/ProductThumb";
import { centsToPeso, mediaUrl } from "../../lib/format";
import styles from "./buyer.module.css";

export default function ProductFeedCard({ listing, onOpen }) {
  return (
    <button type="button" className={styles.card} onClick={onOpen}>
      <ProductThumb
        name={listing.productName}
        category={listing.category}
        size="lg"
        photoUrl={mediaUrl(listing.photoUrl)}
      />
      <div className={styles["card-seller"]}>{listing.sellerName}</div>
      <div className={styles["card-product"]}>{listing.productName}</div>
      <div className={styles["card-meta"]}>
        <span className={styles["card-price"]}>
          {centsToPeso(listing.priceCents)}/{listing.unitLabel}
        </span>
        <Badge tone={listing.badgeTone}>{listing.badgeLabel}</Badge>
      </div>
    </button>
  );
}
