import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "./AuthContext";

export default function ProtectedRoute({ role, children }) {
  const { user, token, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return null;

  if (!token || !user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (role && user.role !== role) {
    return <Navigate to={user.role === "seller" ? "/dashboard" : "/buyer"} replace />;
  }

  return children;
}
