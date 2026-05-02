import type { AppLanguage } from "./uiLexicon";
import type { ClientContext } from "./api";

export function browserLanguage() {
  if (typeof navigator === "undefined") {
    return "es";
  }
  return navigator.language || "es";
}

export function collectClientContext(
  appLanguage: AppLanguage,
  extras?: Partial<ClientContext>,
): ClientContext {
  if (typeof window === "undefined" || typeof navigator === "undefined") {
    return {
      language_app_selected: appLanguage,
      ...extras,
    };
  }

  const connection = (
    navigator as Navigator & {
      connection?: {
        effectiveType?: string;
        rtt?: number;
      };
    }
  ).connection;

  return {
    language_browser: browserLanguage(),
    language_app_selected: appLanguage,
    online_status: navigator.onLine ? "online" : "offline",
    connection_type: connection?.effectiveType,
    estimated_rtt: connection?.rtt,
    ...extras,
  };
}

export function navigationEntryType() {
  if (typeof performance === "undefined") {
    return "navigate";
  }
  const navigation = performance.getEntriesByType(
    "navigation",
  )[0] as PerformanceNavigationTiming | undefined;
  return navigation?.type || "navigate";
}
