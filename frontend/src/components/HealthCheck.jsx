import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";

import apiClient from "../lib/apiClient";

export default function HealthCheck() {
  const { data, isError, error } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiClient.get("/health").then((res) => res.data),
  });

  useEffect(() => {
    if (isError) console.error(`API error: ${error.message}`);
    else if (data) console.log(`API status: ${data.status}`);
  }, [data, isError, error]);

  return null;
}
