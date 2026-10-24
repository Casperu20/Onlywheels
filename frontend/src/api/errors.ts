import { isAxiosError } from "axios";
import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

/** Shape of every error returned by the API (docs/api/CONVENTIONS.md). */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    fields?: Record<string, string[]>;
  };
}

export function getApiError(error: unknown): ApiErrorBody["error"] | null {
  if (isAxiosError<ApiErrorBody>(error) && error.response?.data?.error) {
    return error.response.data.error;
  }
  return null;
}

export function getErrorMessage(error: unknown, fallback: string): string {
  return getApiError(error)?.message ?? fallback;
}

/** Copies API field errors onto react-hook-form fields. Returns true if any were applied. */
export function applyFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fieldMap: Partial<Record<string, Path<T>>> = {},
): boolean {
  const fields = getApiError(error)?.fields;
  if (!fields) return false;

  let applied = false;
  for (const [apiField, messages] of Object.entries(fields)) {
    if (apiField === "non_field_errors") continue;
    const formField = fieldMap[apiField] ?? (apiField as Path<T>);
    if (Array.isArray(messages) && messages.length > 0) {
      setError(formField, { type: "server", message: messages[0] });
      applied = true;
    }
  }
  return applied;
}
