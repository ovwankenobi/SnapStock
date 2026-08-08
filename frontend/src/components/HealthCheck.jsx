import { useQuery } from "@tanstack/react-query";

import apiClient from "../lib/apiClient";

export default function HealthCheck() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.get("/health").then((res) => res.data),
  });

  if (isLoading) return <p>Checking API...</p>;
  if (isError) return <p>API error: {error.message}</p>;
  return <p>API status: {data.status}</p>;
}
