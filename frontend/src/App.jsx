import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import HealthCheck from "./components/HealthCheck";
import { AuthProvider, useAuth } from "./features/auth/AuthContext";
import ForgotPasswordPage from "./features/auth/ForgotPasswordPage";
import LoginPage from "./features/auth/LoginPage";
import ProfilePage from "./features/auth/ProfilePage";
import ProtectedRoute from "./features/auth/ProtectedRoute";
import RegisterPage from "./features/auth/RegisterPage";
import ResetPasswordPage from "./features/auth/ResetPasswordPage";
import BuyerHomePage from "./features/buyer/BuyerHomePage";
import MyReceiptsPage from "./features/buyer/MyReceiptsPage";
import OrderPage from "./features/buyer/OrderPage";
import ProductDetailPage from "./features/buyer/ProductDetailPage";
import SellerPage from "./features/buyer/SellerPage";
import SellerDashboardPage from "./features/dashboard/SellerDashboardPage";
import InventoryPage from "./features/inventory/InventoryPage";
import ProductFormPage from "./features/inventory/ProductFormPage";
import ChatPage from "./features/messages/ChatPage";
import ConversationListPage from "./features/messages/ConversationListPage";
import AnalyticsPage from "./features/analytics/AnalyticsPage";
import CheckoutPage from "./features/sales/CheckoutPage";
import PublicReceiptPage from "./features/sales/PublicReceiptPage";
import ReceiptPage from "./features/sales/ReceiptPage";
import TransactionsPage from "./features/sales/TransactionsPage";

const queryClient = new QueryClient();

function RootRedirect() {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "seller" ? "/dashboard" : "/buyer"} replace />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/r/:receiptCode" element={<PublicReceiptPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute role="seller">
            <SellerDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/inventory"
        element={
          <ProtectedRoute role="seller">
            <InventoryPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/inventory/new"
        element={
          <ProtectedRoute role="seller">
            <ProductFormPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/inventory/:productId/edit"
        element={
          <ProtectedRoute role="seller">
            <ProductFormPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/sales"
        element={
          <ProtectedRoute role="seller">
            <CheckoutPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/sales/:saleId/receipt"
        element={
          <ProtectedRoute role="seller">
            <ReceiptPage />
          </ProtectedRoute>
        }
      />
      {/* Online orders to approve now live under New Sale → Buyer Account. */}
      <Route path="/sales/orders" element={<Navigate to="/sales?path=account" replace />} />
      <Route
        path="/transactions"
        element={
          <ProtectedRoute role="seller">
            <TransactionsPage />
          </ProtectedRoute>
        }
      />
      <Route path="/sales/history" element={<Navigate to="/transactions" replace />}
      />
      <Route
        path="/analytics"
        element={
          <ProtectedRoute role="seller">
            <AnalyticsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/messages"
        element={
          <ProtectedRoute>
            <ConversationListPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/messages/:conversationId"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/buyer"
        element={
          <ProtectedRoute role="buyer">
            <BuyerHomePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/buyer/products/:productId"
        element={
          <ProtectedRoute role="buyer">
            <ProductDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/buyer/sellers/:sellerId"
        element={
          <ProtectedRoute role="buyer">
            <SellerPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/buyer/receipts"
        element={
          <ProtectedRoute role="buyer">
            <MyReceiptsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/buyer/orders/:saleId"
        element={
          <ProtectedRoute role="buyer">
            <OrderPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <HealthCheck />
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
