export const AUTH_STORAGE_KEY = "dreamaxis.auth.token";
export const USER_STORAGE_KEY = "dreamaxis.auth.user";
export const APP_CONFIG_STORAGE_KEY = "dreamaxis.app.config";

export function getAuthToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(AUTH_STORAGE_KEY);
}

export function setAuthToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(AUTH_STORAGE_KEY, token);
}

export function getStoredUser<T = unknown>() {
  if (typeof window === "undefined") return null;
  const value = window.localStorage.getItem(USER_STORAGE_KEY);
  if (!value) return null;
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
}

export function setStoredUser(user: unknown) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

export function getStoredAppConfig<T = unknown>() {
  if (typeof window === "undefined") return null;
  const value = window.localStorage.getItem(APP_CONFIG_STORAGE_KEY);
  if (!value) return null;
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
}

export function setStoredAppConfig(config: unknown) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(APP_CONFIG_STORAGE_KEY, JSON.stringify(config));
}

export function clearAuthToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
  window.localStorage.removeItem(USER_STORAGE_KEY);
}
