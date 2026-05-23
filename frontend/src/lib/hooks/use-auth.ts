"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi, setAuthToken } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

export function useSyncUserToBackend() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Parameters<typeof authApi.githubCallback>[0]) =>
      authApi.githubCallback(data).then((r) => r.data),
    onSuccess: (data) => {
      if (data?.access_token) {
        setAuthToken(data.access_token);
      }
      queryClient.invalidateQueries({ queryKey: queryKeys.auth.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.github.all });
      queryClient.invalidateQueries({
        queryKey: queryKeys.issues.matches(),
      });
    },
    retry: 1,
  });
}
