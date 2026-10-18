// `labelKey` is the full label (sidebar); `shortLabelKey` is the phone bottom-bar label.
// `primary` renders as the raised center action on phones. `end` stops parent routes
// (e.g. "/buyer") from staying highlighted on child routes. `showUserName` labels the item with
// the signed-in user's name (full in the sidebar, first name on the bottom bar).
export function sellerNavItems() {
  return [
    { to: "/dashboard", labelKey: "nav.home", icon: "home" },
    { to: "/messages", labelKey: "nav.messages", icon: "chat" },
    { to: "/inventory", labelKey: "nav.inventory", icon: "box" },
    { to: "/sales", labelKey: "nav.newSale", shortLabelKey: "nav.sell", icon: "plus", primary: true },
    { to: "/analytics", labelKey: "nav.analytics", icon: "chart" },
    { to: "/transactions", labelKey: "nav.transactions", icon: "receipt" },
    { to: "/profile", labelKey: "nav.profile", icon: "user", showUserName: true },
  ];
}

export function buyerNavItems() {
  return [
    { to: "/buyer", labelKey: "nav.discover", icon: "home", end: true },
    { to: "/messages", labelKey: "nav.messages", icon: "chat" },
    { to: "/buyer/receipts", labelKey: "nav.transactions", icon: "receipt" },
    { to: "/profile", labelKey: "nav.profile", icon: "user", showUserName: true },
  ];
}
