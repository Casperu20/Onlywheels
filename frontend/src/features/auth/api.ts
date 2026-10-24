import { apiClient } from "@/api/http";

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
  login: (data: LoginPayload) => apiClient<User>({ url: `${AUTH}/login/`, method: "POST", data }),
  register: (data: RegisterPayload) =>
    apiClient<User>({ url: `${AUTH}/register/`, method: "POST", data }),
  google: (credential: string) =>
    apiClient<User>({ url: `${AUTH}/google/`, method: "POST", data: { credential } }),
  logout: () => apiClient<void>({ url: `${AUTH}/logout/`, method: "POST" }),
  requestPasswordReset: (email: string) =>
    apiClient<void>({ url: `${AUTH}/password/reset/`, method: "POST", data: { email } }),
  confirmPasswordReset: (data: PasswordResetConfirmPayload) =>
    apiClient<void>({ url: `${AUTH}/password/reset/confirm/`, method: "POST", data }),
  exportData: () => apiClient<Record<string, unknown>>({ url: `${AUTH}/me/export/`, method: "GET" }),
  deleteAccount: (data: DeleteAccountPayload) =>
    apiClient<void>({ url: `${AUTH}/me/delete/`, method: "POST", data }),
};
