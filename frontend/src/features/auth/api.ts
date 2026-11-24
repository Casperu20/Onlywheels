import { apiClient } from "@/api/http";
import { clearNativeTokens, getNativeTokens, isNativePlatform, setNativeTokens } from "@/lib/native";

// Hand-written until the orval client is generated; keep in sync with apps/accounts/serializers.py.
export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  preferred_language: "ro" | "en";
  date_joined: string;
  /** false for accounts created with Google only */
  has_password: boolean;
}

export interface DeleteAccountPayload {
  password?: string;
  confirm_email?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload extends LoginPayload {
  first_name?: string;
  last_name?: string;
}

export interface PasswordResetConfirmPayload {
  uid: string;
  token: string;
  new_password: string;
}

const AUTH = "/api/v1/auth";

export const authApi = {
  me: () => apiClient<User>({ url: `${AUTH}/me/`, method: "GET" }),
  updateMe: (data: Partial<Pick<User, "first_name" | "last_name" | "phone" | "preferred_language">>) =>
    apiClient<User>({ url: `${AUTH}/me/`, method: "PATCH", data }),
  login: async (data: LoginPayload) => {
    if (!isNativePlatform()) return apiClient<User>({ url: `${AUTH}/login/`, method: "POST", data });
    const response = await apiClient<{ user: User; access: string; refresh: string }>({
      url: `${AUTH}/native/login/`,
      method: "POST",
      data,
    });
    await setNativeTokens({ access: response.access, refresh: response.refresh });
    return response.user;
  },
  register: async (data: RegisterPayload) => {
    if (!isNativePlatform()) return apiClient<User>({ url: `${AUTH}/register/`, method: "POST", data });
    const response = await apiClient<{ user: User; access: string; refresh: string }>({
      url: `${AUTH}/native/register/`,
      method: "POST",
      data,
    });
    await setNativeTokens({ access: response.access, refresh: response.refresh });
    return response.user;
  },
  google: (credential: string) => {
    if (isNativePlatform()) {
      return Promise.reject(new Error("Google sign-in is not available in the Android app."));
    }
    return apiClient<User>({ url: `${AUTH}/google/`, method: "POST", data: { credential } });
  },
  logout: async () => {
    if (!isNativePlatform()) return apiClient<void>({ url: `${AUTH}/logout/`, method: "POST" });
    const tokens = await getNativeTokens();
    try {
      return await apiClient<void>({
        url: `${AUTH}/native/logout/`,
        method: "POST",
        data: { refresh: tokens?.refresh },
      });
    } finally {
      await clearNativeTokens();
    }
  },
  requestPasswordReset: (email: string) =>
    apiClient<void>({ url: `${AUTH}/password/reset/`, method: "POST", data: { email } }),
  confirmPasswordReset: (data: PasswordResetConfirmPayload) =>
    apiClient<void>({ url: `${AUTH}/password/reset/confirm/`, method: "POST", data }),
  exportData: () => apiClient<Record<string, unknown>>({ url: `${AUTH}/me/export/`, method: "GET" }),
  deleteAccount: async (data: DeleteAccountPayload) => {
    const response = await apiClient<void>({ url: `${AUTH}/me/delete/`, method: "POST", data });
    if (isNativePlatform()) {
      await clearNativeTokens();
    }
    return response;
  },
};
