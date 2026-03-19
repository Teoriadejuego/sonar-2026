import type { AppLanguage } from "./uiLexicon";
import type { ClientContext } from "./api";

function parseUserAgent(userAgent: string) {
  let browserFamily = "Unknown";
  let browserVersion: string | undefined;
  let osFamily = "Unknown";
  let osVersion: string | undefined;
  let deviceType: string = "desktop";

  const browserPatterns: Array<[string, string]> = [
    ["Edg/", "Edge"],
    ["OPR/", "Opera"],
    ["CriOS/", "Chrome"],
    ["Chrome/", "Chrome"],
    ["FxiOS/", "Firefox"],
    ["Firefox/", "Firefox"],
    ["Version/", "Safari"],
  ];

  for (const [marker, family] of browserPatterns) {
    if (userAgent.includes(marker)) {
      browserFamily = family;
      browserVersion = userAgent.split(marker, 2)[1]?.split(" ", 1)[0];
      break;
    }
  }

  if (userAgent.includes("Android")) {
    osFamily = "Android";
    osVersion = userAgent.split("Android", 2)[1]?.split(";", 1)[0]?.trim();
    deviceType = userAgent.includes("Mobile") ? "mobile" : "tablet";
  } else if (userAgent.includes("iPhone")) {
    osFamily = "iOS";
    osVersion = userAgent.split("OS ", 2)[1]?.split(" ", 1)[0]?.replace(/_/g, ".");
    deviceType = "mobile";
  } else if (userAgent.includes("iPad")) {
    osFamily = "iPadOS";
    osVersion = userAgent.split("OS ", 2)[1]?.split(" ", 1)[0]?.replace(/_/g, ".");
    deviceType = "tablet";
  } else if (userAgent.includes("Windows NT")) {
    osFamily = "Windows";
    osVersion = userAgent.split("Windows NT", 2)[1]?.split(";", 1)[0]?.trim();
  } else if (userAgent.includes("Mac OS X")) {
    osFamily = "macOS";
    osVersion = userAgent
      .split("Mac OS X", 2)[1]
      ?.split(")", 1)[0]
      ?.trim()
      ?.replace(/_/g, ".");
  } else if (userAgent.includes("Linux")) {
    osFamily = "Linux";
  }

  if (deviceType === "desktop" && userAgent.includes("Mobile")) {
    deviceType = "mobile";
  }

  return {
    browserFamily,
    browserVersion,
    osFamily,
    osVersion,
    deviceType,
  };
}

function currentOrientation() {
  if (typeof window === "undefined") {
    return undefined;
  }
  if (window.screen.orientation?.type) {
    return window.screen.orientation.type;
  }
  return window.innerWidth >= window.innerHeight ? "landscape" : "portrait";
}

function colorSchemePreference() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return undefined;
  }
  if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }
  if (window.matchMedia("(prefers-color-scheme: light)").matches) {
    return "light";
  }
  return "no-preference";
}

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

  const userAgent = navigator.userAgent || "";
  const parsedUa = parseUserAgent(userAgent);
  const connection = (
    navigator as Navigator & {
      connection?: {
        effectiveType?: string;
        downlink?: number;
        rtt?: number;
      };
    }
  ).connection;

  return {
    user_agent_raw: userAgent,
    browser_family: parsedUa.browserFamily,
    browser_version: parsedUa.browserVersion,
    os_family: parsedUa.osFamily,
    os_version: parsedUa.osVersion,
    device_type: parsedUa.deviceType,
    platform: navigator.platform || undefined,
    language_browser: browserLanguage(),
    language_app_selected: appLanguage,
    screen_width: window.screen.width,
    screen_height: window.screen.height,
    viewport_width: window.innerWidth,
    viewport_height: window.innerHeight,
    device_pixel_ratio: window.devicePixelRatio || 1,
    orientation: currentOrientation(),
    touch_capable:
      "ontouchstart" in window || (navigator.maxTouchPoints ?? 0) > 0,
    hardware_concurrency: navigator.hardwareConcurrency || undefined,
    max_touch_points: navigator.maxTouchPoints || undefined,
    color_scheme_preference: colorSchemePreference(),
    online_status: navigator.onLine ? "online" : "offline",
    connection_type: connection?.effectiveType,
    estimated_downlink: connection?.downlink,
    estimated_rtt: connection?.rtt,
    timezone_offset_minutes: new Date().getTimezoneOffset(),
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
