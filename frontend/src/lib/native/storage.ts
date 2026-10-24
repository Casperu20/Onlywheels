/**
 * Small key-value storage for non-sensitive data. Web: localStorage; Android: @capacitor/preferences.
 * Auth tokens are NOT stored here on the web (they live in httpOnly cookies).
 */
export const storage = {
  get(key: string): string | null {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key: string, value: string): void {
    try {
      localStorage.setItem(key, value);
    } catch {
      // storage full or disabled (private mode) – ignore
    }
  },
  remove(key: string): void {
    try {
      localStorage.removeItem(key);
    } catch {
      // ignore
    }
  },
};
