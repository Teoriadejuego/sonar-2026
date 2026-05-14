type ShareResult = "opened" | "cancelled";

const WHATSAPP_APP_FALLBACK_DELAY_MS = 900;

function isProbablyMobileDevice() {
  if (typeof window === "undefined") {
    return false;
  }
  const userAgent = window.navigator.userAgent.toLowerCase();
  const mobilePattern =
    /android|iphone|ipad|ipod|mobile|windows phone|opera mini/i;
  return (
    mobilePattern.test(userAgent) ||
    window.navigator.maxTouchPoints > 1 ||
    window.matchMedia?.("(pointer: coarse)")?.matches === true
  );
}

function buildWhatsappUrls(message: string) {
  const encodedMessage = encodeURIComponent(message);
  return {
    appUrl: `whatsapp://send?text=${encodedMessage}`,
    universalUrl: `https://api.whatsapp.com/send?text=${encodedMessage}`,
    webUrl: `https://web.whatsapp.com/send?text=${encodedMessage}`,
  };
}

function openMobileWhatsapp(appUrl: string, universalUrl: string) {
  if (typeof window === "undefined") {
    return;
  }

  let cleanedUp = false;
  let appOpened = false;

  const cleanup = () => {
    if (cleanedUp) {
      return;
    }
    cleanedUp = true;
    document.removeEventListener("visibilitychange", handleVisibilityChange);
    window.removeEventListener("pagehide", handlePageHide);
    window.clearTimeout(fallbackTimer);
  };

  const handleVisibilityChange = () => {
    if (document.visibilityState === "hidden") {
      appOpened = true;
      cleanup();
    }
  };

  const handlePageHide = () => {
    appOpened = true;
    cleanup();
  };

  const fallbackTimer = window.setTimeout(() => {
    cleanup();
    if (!appOpened && document.visibilityState === "visible") {
      window.location.assign(universalUrl);
    }
  }, WHATSAPP_APP_FALLBACK_DELAY_MS);

  document.addEventListener("visibilitychange", handleVisibilityChange);
  window.addEventListener("pagehide", handlePageHide);
  window.location.assign(appUrl);
}

export async function openWhatsAppShare(message: string): Promise<ShareResult> {
  if (typeof window === "undefined") {
    return "cancelled";
  }

  const normalizedMessage = message.trim();
  if (!normalizedMessage) {
    return "cancelled";
  }

  const { appUrl, universalUrl, webUrl } = buildWhatsappUrls(normalizedMessage);
  const isMobile = isProbablyMobileDevice();

  if (!isMobile) {
    const popup = window.open(webUrl, "_blank", "noopener,noreferrer");
    if (!popup) {
      window.location.assign(universalUrl);
    }
    return "opened";
  }

  openMobileWhatsapp(appUrl, universalUrl);
  return "opened";
}
