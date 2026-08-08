export function sellerNavItems() {
  return [
    { to: "/dashboard", label: "Home", icon: "home" },
    { to: "/inventory", label: "Inventory", icon: "box" },
    { to: "/sales", label: "New Sale", icon: "plus" },
    { to: "/analytics", label: "Sales History", icon: "chart" },
    { to: "/messages", label: "Messages", icon: "chat" },
  ];
}

export function buyerNavItems() {
  return [
    { to: "/buyer", label: "Discover", icon: "home" },
    { to: "/buyer/receipts", label: "Receipts", icon: "receipt" },
    { to: "/messages", label: "Messages", icon: "chat" },
  ];
}
