import { useCallback, useEffect } from "react";
import { initializeTelemetryQueue } from "./telemetryQueue";

type TrackClickOptions = {
  payload?: Record<string, unknown>;
  value?: number;
  target?: string;
  role?: string;
  ctaKind?: "primary" | "secondary" | "tertiary";
};

const NOOP_TRACK_CLICK = (
  _eventName?: string,
  _options?: TrackClickOptions,
) => {
  return;
};

export function usePageTelemetry(_screenName: string) {
  useEffect(() => {
    initializeTelemetryQueue();
  }, []);

  const trackClick = useCallback(NOOP_TRACK_CLICK, []);

  return { trackClick, spellId: null };
}
