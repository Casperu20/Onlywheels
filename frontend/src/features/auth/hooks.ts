import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";

import { authApi, type User } from "./api";

export const meQueryKey = ["auth", "me"] as const;

/** Current user, or `null` when logged out. */
export function useMe() {
  return useQuery<User | null>({
    queryKey: meQueryKey,
    queryFn: async () => {
      try {
        return await authApi.me();
      } catch (error) {
        if (isAxiosError(error) && error.response?.status === 401) return null;
        throw error;
      }
    },
    staleTime: 5 * 60_000,
  });
}

function useSetSession() {
  const queryClient = useQueryClient();
  return (user: User) => queryClient.setQueryData(meQueryKey, user);
}

export function useLogin() {
  const setSession = useSetSession();
  return useMutation({ mutationFn: authApi.login, onSuccess: setSession });
}

export function useRegister() {
  const setSession = useSetSession();
  return useMutation({ mutationFn: authApi.register, onSuccess: setSession });
}

export function useGoogleLogin() {
  const setSession = useSetSession();
  return useMutation({ mutationFn: authApi.google, onSuccess: setSession });
}

export function useLogout() {
  const clearSession = useClearSession();
  return useMutation({ mutationFn: authApi.logout, onSettled: clearSession });
}

export function useDeleteAccount() {
  const clearSession = useClearSession();
  return useMutation({ mutationFn: authApi.deleteAccount, onSuccess: clearSession });
}

function useClearSession() {
  const queryClient = useQueryClient();
  return () => {
    // Drop every cached response that belonged to the previous user.
    queryClient.clear();
    queryClient.setQueryData(meQueryKey, null);
  };
}

export function useRequestPasswordReset() {
  return useMutation({ mutationFn: authApi.requestPasswordReset });
}

export function useConfirmPasswordReset() {
  return useMutation({ mutationFn: authApi.confirmPasswordReset });
}
