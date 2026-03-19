import { useEffect, useMemo, useRef } from "react";
import { useLanguage } from "./LanguageContext";
import { useSession } from "./SessionContext";
import { navigationEntryType } from "./clientContext";

type TrackClickOptions = {
  payload?: Record<string, unknown>;
  value?: number;
  target?: string;
  role?: string;
  ctaKind?: "primary" | "secondary" | "tertiary";
};

type SpellMetrics = {
  spellId: string;
  startedAt: number;
  visibleStartedAt: number | null;
  blurStartedAt: number | null;
  hiddenStartedAt: number | null;
  visibleMs: number;
  blurMs: number;
  hiddenMs: number;
  focusChangeCount: number;
  visibilityChangeCount: number;
  clickCount: number;
  primaryClickCount: number;
  secondaryClickCount: number;
  firstClickMs: number | null;
  primaryCtaMs: number | null;
  secondaryCtaMs: number | null;
  firstClickTarget: string | null;
  clickTargets: string[];
  languageAtEntry: string;
  languageAtExit: string;
  languageChangedDuringSpell: boolean;
};

function makeSpellId(screenName: string) {
  return typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? `${screenName}-${crypto.randomUUID()}`
    : `${screenName}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function usePageTelemetry(screenName: string) {
  const { pushTelemetry } = useSession();
  const { language } = useLanguage();
  const metricsRef = useRef<SpellMetrics | null>(null);
  const isVisibleRef = useRef(true);
  const isFocusedRef = useRef(true);

  const spellId = useMemo(() => makeSpellId(screenName), [screenName]);

  useEffect(() => {
    const startedAt = Date.now();
    metricsRef.current = {
      spellId,
      startedAt,
      visibleStartedAt: startedAt,
      blurStartedAt: null,
      hiddenStartedAt: null,
      visibleMs: 0,
      blurMs: 0,
      hiddenMs: 0,
      focusChangeCount: 0,
      visibilityChangeCount: 0,
      clickCount: 0,
      primaryClickCount: 0,
      secondaryClickCount: 0,
      firstClickMs: null,
      primaryCtaMs: null,
      secondaryCtaMs: null,
      firstClickTarget: null,
      clickTargets: [],
      languageAtEntry: language,
      languageAtExit: language,
      languageChangedDuringSpell: false,
    };
    isVisibleRef.current = typeof document === "undefined"
      ? true
      : document.visibilityState !== "hidden";
    isFocusedRef.current =
      typeof document === "undefined" ? true : document.hasFocus();

    pushTelemetry({
      event_type: "screen_enter",
      event_name: "screen_enter",
      screen_name: screenName,
      client_ts: startedAt,
      spell_id: spellId,
      app_language: language,
      payload: {
        entry_origin: navigationEntryType(),
        entered_via_resume: navigationEntryType() === "reload",
        screen_name: screenName,
      },
    });

    const onFocus = () => {
      const metrics = metricsRef.current;
      if (!metrics || isFocusedRef.current) {
        return;
      }
      const now = Date.now();
      metrics.focusChangeCount += 1;
      if (metrics.blurStartedAt) {
        metrics.blurMs += now - metrics.blurStartedAt;
        metrics.blurStartedAt = null;
      }
      isFocusedRef.current = true;
      pushTelemetry({
        event_type: "lifecycle",
        event_name: "focus",
        screen_name: screenName,
        client_ts: now,
        spell_id: spellId,
        app_language: language,
      });
    };

    const onBlur = () => {
      const metrics = metricsRef.current;
      if (!metrics || !isFocusedRef.current) {
        return;
      }
      const now = Date.now();
      metrics.focusChangeCount += 1;
      metrics.blurStartedAt = now;
      isFocusedRef.current = false;
      pushTelemetry({
        event_type: "lifecycle",
        event_name: "blur",
        screen_name: screenName,
        client_ts: now,
        spell_id: spellId,
        app_language: language,
      });
    };

    const onVisibility = () => {
      const metrics = metricsRef.current;
      if (!metrics) {
        return;
      }
      const now = Date.now();
      metrics.visibilityChangeCount += 1;
      const hidden = document.visibilityState === "hidden";
      if (hidden) {
        if (metrics.visibleStartedAt) {
          metrics.visibleMs += now - metrics.visibleStartedAt;
          metrics.visibleStartedAt = null;
        }
        metrics.hiddenStartedAt = now;
      } else {
        if (metrics.hiddenStartedAt) {
          metrics.hiddenMs += now - metrics.hiddenStartedAt;
          metrics.hiddenStartedAt = null;
        }
        metrics.visibleStartedAt = now;
      }
      isVisibleRef.current = !hidden;
      pushTelemetry({
        event_type: "lifecycle",
        event_name: hidden ? "visibility_hidden" : "visibility_visible",
        screen_name: screenName,
        client_ts: now,
        spell_id: spellId,
        app_language: language,
        visibility_state: document.visibilityState,
      });
    };

    const onLanguageChanged = (event: Event) => {
      const detail = (event as CustomEvent<{ language: string }>).detail;
      const metrics = metricsRef.current;
      if (!metrics || !detail?.language) {
        return;
      }
      metrics.languageAtExit = detail.language;
      metrics.languageChangedDuringSpell =
        metrics.languageChangedDuringSpell ||
        detail.language !== metrics.languageAtEntry;
      pushTelemetry({
        event_type: "lifecycle",
        event_name: "language_change",
        screen_name: screenName,
        client_ts: Date.now(),
        spell_id: spellId,
        app_language: detail.language,
        payload: {
          previous_language: metrics.languageAtEntry,
          next_language: detail.language,
        },
      });
    };

    window.addEventListener("focus", onFocus);
    window.addEventListener("blur", onBlur);
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("sonar_language_changed", onLanguageChanged as EventListener);

    return () => {
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("blur", onBlur);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener(
        "sonar_language_changed",
        onLanguageChanged as EventListener,
      );

      const metrics = metricsRef.current;
      if (!metrics) {
        return;
      }
      const endedAt = Date.now();
      if (metrics.visibleStartedAt) {
        metrics.visibleMs += endedAt - metrics.visibleStartedAt;
      }
      if (metrics.hiddenStartedAt) {
        metrics.hiddenMs += endedAt - metrics.hiddenStartedAt;
      }
      if (metrics.blurStartedAt) {
        metrics.blurMs += endedAt - metrics.blurStartedAt;
      }
      pushTelemetry({
        event_type: "screen_exit",
        event_name: "screen_exit",
        screen_name: screenName,
        client_ts: endedAt,
        duration_ms: endedAt - metrics.startedAt,
        spell_id: metrics.spellId,
        app_language: metrics.languageAtExit,
        payload: {
          screen_name: screenName,
          visible_ms: metrics.visibleMs,
          hidden_ms: metrics.hiddenMs,
          blur_ms: metrics.blurMs,
          focus_change_count: metrics.focusChangeCount,
          visibility_change_count: metrics.visibilityChangeCount,
          click_count: metrics.clickCount,
          primary_click_count: metrics.primaryClickCount,
          secondary_click_count: metrics.secondaryClickCount,
          first_click_ms: metrics.firstClickMs,
          primary_cta_ms: metrics.primaryCtaMs,
          secondary_cta_ms: metrics.secondaryCtaMs,
          first_click_target: metrics.firstClickTarget,
          click_targets: metrics.clickTargets,
          language_changed_during_spell: metrics.languageChangedDuringSpell,
          language_at_entry: metrics.languageAtEntry,
          language_at_exit: metrics.languageAtExit,
        },
      });
      metricsRef.current = null;
    };
  }, [language, pushTelemetry, screenName, spellId]);

  const trackClick = (
    eventName: string,
    options?: TrackClickOptions,
  ) => {
    const now = Date.now();
    const metrics = metricsRef.current;
    const target = options?.target ?? eventName;
    if (metrics) {
      const elapsed = now - metrics.startedAt;
      metrics.clickCount += 1;
      if (options?.ctaKind === "primary") {
        metrics.primaryClickCount += 1;
        if (metrics.primaryCtaMs === null) {
          metrics.primaryCtaMs = elapsed;
        }
      }
      if (options?.ctaKind === "secondary") {
        metrics.secondaryClickCount += 1;
        if (metrics.secondaryCtaMs === null) {
          metrics.secondaryCtaMs = elapsed;
        }
      }
      if (metrics.firstClickMs === null) {
        metrics.firstClickMs = elapsed;
        metrics.firstClickTarget = target;
      }
      metrics.clickTargets.push(target);
      metrics.languageAtExit = language;
    }

    pushTelemetry({
      event_type: "click",
      event_name: eventName,
      screen_name: screenName,
      client_ts: now,
      spell_id: spellId,
      app_language: language,
      value: options?.value,
      interaction_target: target,
      interaction_role: options?.role,
      cta_kind: options?.ctaKind,
      payload: options?.payload,
    });
  };

  return { trackClick, spellId };
}
