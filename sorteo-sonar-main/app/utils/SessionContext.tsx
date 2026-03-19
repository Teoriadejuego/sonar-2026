import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  accessSession,
  captureDisplaySnapshot,
  DEFAULT_PUBLIC_CONFIG,
  fetchPublicConfig,
  paymentLookup,
  paymentSubmit,
  postTelemetryBatch,
  prepareReport,
  resumeSession,
  rollSession,
  submitInterestSignup as submitInterestSignupRequest,
  submitReport,
  updateScreenCursor,
  setApiTelemetryReporter,
  type PublicConfig,
  type ScreenCursor,
  type SessionPayload,
  type TelemetryEventRequest,
  type DisplaySnapshotRequest,
  type PaymentLookupResponse,
  type PaymentSubmitResponse,
  type InterestSignupResponse,
  type ClientContext,
  type ClientContextSummary,
  type SnapshotRecordSummary,
  UserNotFoundError,
} from "./api";
import { useLanguage } from "./LanguageContext";
import { browserLanguage, collectClientContext } from "./clientContext";
import { UI_LEXICON, formatCopy, type AppLanguage } from "./uiLexicon";

type AccessResult =
  | { success: true; session: SessionPayload }
  | { success: false; error: string; isNotFound: boolean };

type ConsentPayload = {
  ageConfirmed: boolean;
  participationAccepted: boolean;
  dataAccepted: boolean;
};

type LandingMetrics = {
  landingVisibleMs?: number;
  infoPanelsOpened?: string[];
  infoPanelDurationsMs?: Record<string, number>;
  checkboxOrder?: string[];
  checkboxTimestampsMs?: Record<string, number>;
  continueBlockedCount?: number;
};

type StoredSessionState = {
  sessionId?: string;
  braceletId?: string;
  demoSession?: SessionPayload | null;
};

type SessionContextValue = {
  publicConfig: PublicConfig;
  session: SessionPayload | null;
  braceletId: string;
  isLoading: boolean;
  isHydrating: boolean;
  startSession: (
    braceletId: string,
    consents: ConsentPayload,
    metrics?: LandingMetrics,
  ) => Promise<AccessResult>;
  moveToScreen: (screen: ScreenCursor) => Promise<void>;
  rollNext: (reactionMs?: number) => Promise<number>;
  prepareForReport: () => Promise<void>;
  submitClaim: (reportedValue: number, reactionMs?: number) => Promise<void>;
  saveDisplaySnapshot: (payload: DisplaySnapshotRequest) => Promise<void>;
  lookupPaymentCode: (code: string) => Promise<PaymentLookupResponse>;
  submitPaymentRequest: (
    code: string,
    phone: string,
    donationRequested?: boolean,
    messageText?: string,
  ) => Promise<PaymentSubmitResponse>;
  submitInterestSignup: (email: string) => Promise<InterestSignupResponse>;
  pushTelemetry: (event: TelemetryEventRequest) => void;
  clearLocalSession: () => void;
};

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

const STORAGE_KEY = "sonar_session_v2";
const TELEMETRY_KEY = "sonar_telemetry_v2";
const INSTALLATION_KEY = "sonar_installation_v1";
const EVENT_SEQUENCE_KEY = "sonar_event_sequence_v1";
const DEMO_SESSION_PREFIX = "demo-session-";

type DemoScenario = {
  braceletId: string;
  treatmentKey: string;
  treatmentFamily: string;
  countTarget: number | null;
  targetValue: number | null;
  selectedForPayment: boolean;
  throwSequence: number[];
  referenceCode: string | null;
};

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") {
    return fallback;
  }
  const raw = window.localStorage.getItem(key);
  if (!raw) {
    return fallback;
  }
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(key, JSON.stringify(value));
}

function readNumber(key: string, fallback: number) {
  if (typeof window === "undefined") {
    return fallback;
  }
  const raw = window.localStorage.getItem(key);
  if (!raw) {
    return fallback;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function writeNumber(key: string, value: number) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(key, String(value));
}

function getInstallationId() {
  if (typeof window === "undefined") {
    return "server";
  }
  const existing = window.localStorage.getItem(INSTALLATION_KEY);
  if (existing) {
    return existing;
  }
  const next =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `install-${Date.now()}`;
  window.localStorage.setItem(INSTALLATION_KEY, next);
  return next;
}

function makeIdempotencyKey(prefix: string) {
  return typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? `${prefix}-${crypto.randomUUID()}`
    : `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function readReferralParams() {
  if (typeof window === "undefined") {
    return {
      referralCode: null,
      referralSource: null,
      referralMedium: null,
      referralCampaign: null,
      referralLinkId: null,
      qrEntryCode: null,
      referralPath: null,
    };
  }
  const url = new URL(window.location.href);
  const qrEntryCode =
    url.searchParams.get("qr") ??
    url.searchParams.get("qr_id") ??
    url.searchParams.get("poster") ??
    url.searchParams.get("poster_id") ??
    url.searchParams.get("cartel") ??
    url.searchParams.get("cartel_id");
  const explicitSource = url.searchParams.get("src");
  const explicitMedium =
    url.searchParams.get("utm_medium") ?? url.searchParams.get("medium");
  return {
    referralCode: url.searchParams.get("ref"),
    referralSource: explicitSource ?? (qrEntryCode ? "qr" : null),
    referralMedium: explicitMedium ?? (qrEntryCode ? "offline_poster" : null),
    referralCampaign:
      url.searchParams.get("utm_campaign") ?? url.searchParams.get("campaign"),
    referralLinkId: url.searchParams.get("link_id") ?? qrEntryCode,
    qrEntryCode,
    referralPath: `${url.pathname}${url.search}`,
  };
}

function isExperimentPausedError(message: string) {
  return /temporalmente detenido/i.test(message);
}

function resolveDemoTreatment(
  publicConfig: PublicConfig,
  braceletId: string,
): Pick<DemoScenario, "treatmentKey" | "treatmentFamily" | "countTarget" | "targetValue"> | null {
  const normalized = braceletId.trim().toUpperCase();
  const nonControlTreatments = publicConfig.treatments.filter(
    (item) => item !== "control",
  );

  if (normalized === "12341") {
    return {
      treatmentKey: "control",
      treatmentFamily: "control",
      countTarget: null,
      targetValue: null,
    };
  }
  if (normalized === "12342" || normalized === "12343") {
    const index = normalized === "12342" ? 0 : 1;
    const treatmentKey =
      nonControlTreatments[index] ??
      nonControlTreatments[0] ??
      "control";
    const targetValue = publicConfig.treatment_targets[treatmentKey] ?? null;
    return {
      treatmentKey,
      treatmentFamily:
        treatmentKey === "control"
          ? "control"
          : targetValue === 5
            ? "five_norm"
            : "six_norm",
      countTarget: publicConfig.seed_initial_counts[treatmentKey] ?? null,
      targetValue,
    };
  }
  return null;
}

function getDemoScenario(
  publicConfig: PublicConfig,
  braceletId: string,
): DemoScenario | null {
  const normalized = braceletId.trim().toUpperCase();
  if (normalized === "1234") {
    return {
      braceletId: normalized,
      treatmentKey: "control",
      treatmentFamily: "control",
      countTarget: null,
      targetValue: null,
      selectedForPayment: true,
      throwSequence: [6, 4, 5, 3, 6, 2, 4, 5, 1, 6],
      referenceCode: "#demo60",
    };
  }

  const treatment = resolveDemoTreatment(publicConfig, normalized);
  if (!treatment) {
    return null;
  }

  return {
    braceletId: normalized,
    ...treatment,
    selectedForPayment: false,
    throwSequence:
      normalized === "12341"
        ? [4, 2, 5, 3, 1, 4, 6, 2, 5, 3]
        : normalized === "12342"
          ? [4, 5, 2, 3, 6, 4, 1, 2, 5, 6]
          : [4, 6, 5, 6, 3, 4, 6, 2, 5, 6],
    referenceCode: null,
  };
}

function isDemoSession(session: SessionPayload | null | undefined) {
  return Boolean(session?.session_id?.startsWith(DEMO_SESSION_PREFIX));
}

function getDemoScenarioForSession(
  publicConfig: PublicConfig,
  session: SessionPayload,
  braceletIdValue?: string,
) {
  const resolvedBraceletId =
    braceletIdValue ?? session.session_id.replace(DEMO_SESSION_PREFIX, "");
  return getDemoScenario(publicConfig, resolvedBraceletId);
}

function toClientContextSummary(context: ClientContext): ClientContextSummary {
  return {
    browser_family: context.browser_family ?? null,
    browser_version: context.browser_version ?? null,
    os_family: context.os_family ?? null,
    os_version: context.os_version ?? null,
    device_type: context.device_type ?? null,
    platform: context.platform ?? null,
    language_browser: context.language_browser ?? null,
    language_app_selected: context.language_app_selected ?? null,
    screen_width: context.screen_width ?? null,
    screen_height: context.screen_height ?? null,
    viewport_width: context.viewport_width ?? null,
    viewport_height: context.viewport_height ?? null,
    device_pixel_ratio: context.device_pixel_ratio ?? null,
    orientation: context.orientation ?? null,
    touch_capable: context.touch_capable ?? null,
    hardware_concurrency: context.hardware_concurrency ?? null,
    max_touch_points: context.max_touch_points ?? null,
    color_scheme_preference: context.color_scheme_preference ?? null,
    online_status: context.online_status ?? null,
    connection_type: context.connection_type ?? null,
    estimated_downlink: context.estimated_downlink ?? null,
    estimated_rtt: context.estimated_rtt ?? null,
    timezone_offset_minutes: context.timezone_offset_minutes ?? null,
  };
}

function buildDemoSnapshotRecord(
  session: SessionPayload,
  overrides: Partial<SnapshotRecordSummary> = {},
): SnapshotRecordSummary {
  const base = session.snapshot_record;
  return {
    language_used: overrides.language_used ?? base?.language_used ?? null,
    displayed_message_text:
      overrides.displayed_message_text ?? base?.displayed_message_text ?? null,
    control_message_text:
      overrides.control_message_text ?? base?.control_message_text ?? null,
    final_message_text:
      overrides.final_message_text ?? base?.final_message_text ?? null,
    payout_reference_shown:
      overrides.payout_reference_shown ?? base?.payout_reference_shown ?? null,
    payout_phone_shown:
      overrides.payout_phone_shown ?? base?.payout_phone_shown ?? null,
    first_result_value:
      overrides.first_result_value ?? session.first_result_value ?? null,
    last_seen_value: overrides.last_seen_value ?? session.last_seen_value ?? null,
    all_values_seen:
      overrides.all_values_seen ??
      base?.all_values_seen ??
      session.throws.map((item) => item.result_value),
    rerolls_visible:
      overrides.rerolls_visible ??
      base?.rerolls_visible ??
      session.throws.slice(1).map((item) => item.result_value),
    final_state_shown:
      overrides.final_state_shown ?? base?.final_state_shown ?? null,
  };
}

function buildDemoReportSnapshot(
  publicConfig: PublicConfig,
  language: AppLanguage,
  scenario: DemoScenario,
) {
  const copy = UI_LEXICON[language];
  const message = scenario.treatmentKey === "control"
    ? `${copy.treatment.controlTitle}. ${copy.treatment.controlBody}`
    : formatCopy(copy.treatment.socialMessageTemplate, {
        count: scenario.countTarget ?? "-",
        denominator: publicConfig.window_size,
        target: scenario.targetValue ?? "-",
      });

  return {
    treatment_key: scenario.treatmentKey,
    count_target: scenario.countTarget,
    denominator:
      scenario.treatmentKey === "control" ? null : publicConfig.window_size,
    target_value: scenario.targetValue,
    window_version: 1,
    message,
    message_version: "demo_preview_v1",
    is_control: scenario.treatmentKey === "control",
  };
}

function buildDemoSession(
  publicConfig: PublicConfig,
  language: AppLanguage,
  braceletId: string,
  scenario: DemoScenario,
): SessionPayload {
  return {
    session_id: `${DEMO_SESSION_PREFIX}${scenario.braceletId}`,
    state: "assigned",
    screen: "instructions",
    experiment_version: `${publicConfig.experiment_version}-demo`,
    experiment_phase: publicConfig.current_phase,
    phase_version: "demo_phase_v1",
    phase_activation_status: "demo_preview",
    ui_version: "demo_ui_v1",
    consent_version: "demo_consent_v1",
    treatment_version: publicConfig.treatment_version,
    treatment_text_version: "demo_text_v1",
    allocation_version: publicConfig.allocation_version,
    deck_version: "demo_deck_v1",
    payment_version: "demo_payment_v1",
    telemetry_version: "demo_telemetry_v1",
    lexicon_version: "demo_lexicon_v1",
    treatment_key: scenario.treatmentKey,
    treatment_family: scenario.treatmentFamily,
    norm_target_value: scenario.targetValue,
    language_at_access: language,
    language_at_claim: language,
    language_changed_during_session: false,
    deployment_context: "demo_preview",
    site_code: "DEMO",
    campaign_code: "DEMO",
    environment_label: "demo",
    bracelet_status: "active",
    consent: {
      accepted: true,
      age_confirmed: true,
      info_accepted: true,
      data_accepted: true,
      accepted_at: new Date().toISOString(),
    },
    referral_code: `demo-ref-${scenario.braceletId}`,
    invited_by_session_id: null,
    invited_by_referral_code: null,
    referral_source: null,
    referral_medium: null,
    referral_campaign: null,
    referral_link_id: null,
    qr_entry_code: null,
    referral_landing_path: null,
    referral_arrived_at: null,
    operational_note: null,
    position_index: 0,
    root_sequence: 0,
    selected_for_payment: scenario.selectedForPayment,
    max_attempts: publicConfig.max_attempts,
    first_result_value: null,
    last_seen_value: null,
    max_seen_value: null,
    reroll_count: 0,
    is_valid_completed: false,
    valid_completed_at: null,
    report_snapshot: null,
    throws: [],
    claim: null,
    payment: {
      eligible: scenario.selectedForPayment,
      amount_cents: 0,
      amount_eur: 0,
      status: scenario.selectedForPayment ? "pending" : "not_eligible",
      reference_code: scenario.referenceCode,
    },
    quality_flags: [],
    antifraud_flags: [],
    client_context: null,
    session_metrics: {
      resume_count: 0,
      refresh_count: 0,
      blur_count: 0,
      network_error_count: 0,
      retry_count: 0,
      click_count_total: 0,
      screen_changes_count: 0,
      language_change_count: 0,
      telemetry_event_count: 0,
      max_event_sequence_number: 0,
    },
    consent_record: {
      language_at_access: language,
      landing_visible_ms: null,
      info_panels_opened: [],
      info_panel_durations_ms: {},
      checkbox_order: [],
      checkbox_timestamps_ms: {},
      continue_blocked_count: 0,
    },
    snapshot_record: {
      language_used: language,
      displayed_message_text: null,
      control_message_text: null,
      final_message_text: null,
      payout_reference_shown: scenario.referenceCode,
      payout_phone_shown: null,
      first_result_value: null,
      last_seen_value: null,
      all_values_seen: [],
      rerolls_visible: [],
      final_state_shown: null,
    },
    screen_metrics: null,
    series: {
      experiment_phase: publicConfig.current_phase,
      treatment_key: scenario.treatmentKey,
      treatment_family: scenario.treatmentFamily,
      norm_target_value: scenario.targetValue,
      completed_count: 0,
      visible_count_target: scenario.countTarget ?? 0,
      actual_count_target: scenario.countTarget ?? 0,
      visible_window_version: 1,
      actual_window_version: 1,
    },
  };
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const { language } = useLanguage();
  const [publicConfig, setPublicConfig] =
    useState<PublicConfig>(DEFAULT_PUBLIC_CONFIG);
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [braceletId, setBraceletId] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isHydrating, setIsHydrating] = useState(true);

  const flushInFlightRef = useRef(false);
  const publicConfigRef = useRef<PublicConfig>(DEFAULT_PUBLIC_CONFIG);
  const sessionRef = useRef<SessionPayload | null>(null);
  const telemetryQueueRef = useRef<TelemetryEventRequest[]>(
    readJson<TelemetryEventRequest[]>(TELEMETRY_KEY, []),
  );
  const eventSequenceRef = useRef<number>(readNumber(EVENT_SEQUENCE_KEY, 0));
  const lastLanguageRef = useRef<string>(language);

  const commitSession = useCallback((nextSession: SessionPayload | null) => {
    sessionRef.current = nextSession;
    setSession(nextSession);
  }, []);

  const refreshPublicConfig = useCallback(async () => {
    try {
      const nextConfig = await fetchPublicConfig();
      setPublicConfig(nextConfig);
      return nextConfig;
    } catch {
      return publicConfigRef.current;
    }
  }, []);

  useEffect(() => {
    sessionRef.current = session;
    if (typeof window === "undefined") {
      return;
    }
    if (!session) {
      window.localStorage.removeItem(STORAGE_KEY);
      return;
    }
    const storedSession: StoredSessionState = isDemoSession(session)
      ? {
          sessionId: session.session_id,
          braceletId,
          demoSession: session,
        }
      : {
          sessionId: session.session_id,
          braceletId,
        };
    writeJson(STORAGE_KEY, storedSession);
    const maxKnownSequence = session.session_metrics?.max_event_sequence_number ?? 0;
    if (maxKnownSequence > eventSequenceRef.current) {
      eventSequenceRef.current = maxKnownSequence;
      writeNumber(EVENT_SEQUENCE_KEY, maxKnownSequence);
    }
  }, [session, braceletId]);

  useEffect(() => {
    publicConfigRef.current = publicConfig;
  }, [publicConfig]);

  const nextEventSequenceNumber = useCallback(() => {
    eventSequenceRef.current += 1;
    writeNumber(EVENT_SEQUENCE_KEY, eventSequenceRef.current);
    return eventSequenceRef.current;
  }, []);

  const currentClientContext = useCallback(
    (extras?: Partial<ClientContext>) => collectClientContext(language, extras),
    [language],
  );

  const flushTelemetry = useCallback(async () => {
    if (flushInFlightRef.current) {
      return;
    }
    const currentSession = sessionRef.current;
    if (!currentSession || telemetryQueueRef.current.length === 0) {
      return;
    }
    if (isDemoSession(currentSession)) {
      telemetryQueueRef.current = [];
      writeJson(TELEMETRY_KEY, telemetryQueueRef.current);
      return;
    }

    flushInFlightRef.current = true;
    try {
      const batch = telemetryQueueRef.current.slice(0, 50);
      await postTelemetryBatch(currentSession.session_id, batch);
      telemetryQueueRef.current = telemetryQueueRef.current.slice(batch.length);
      writeJson(TELEMETRY_KEY, telemetryQueueRef.current);
    } catch {
      flushInFlightRef.current = false;
      return;
    }
    flushInFlightRef.current = false;
    if (telemetryQueueRef.current.length > 0) {
      void flushTelemetry();
    }
  }, []);

  useEffect(() => {
    if (session) {
      void flushTelemetry();
    }
  }, [flushTelemetry, session]);

  const pushTelemetry = useCallback(
    (event: TelemetryEventRequest) => {
      const previousLanguage = lastLanguageRef.current;
      const languageChanged =
        event.app_language &&
        previousLanguage &&
        event.app_language !== previousLanguage;
      if (event.app_language) {
        lastLanguageRef.current = event.app_language;
      }
      telemetryQueueRef.current.push({
        ...event,
        client_ts: event.client_ts ?? Date.now(),
        event_sequence_number:
          event.event_sequence_number ?? nextEventSequenceNumber(),
        timezone_offset_minutes:
          event.timezone_offset_minutes ?? new Date().getTimezoneOffset(),
        app_language: event.app_language ?? language,
        browser_language: event.browser_language ?? browserLanguage(),
        network_status:
          event.network_status ??
          (typeof navigator !== "undefined" && !navigator.onLine
            ? "offline"
            : "online"),
        client_context: event.client_context,
        payload: languageChanged
          ? {
              ...event.payload,
              language_changed_from: previousLanguage,
            }
          : event.payload,
      });
      writeJson(TELEMETRY_KEY, telemetryQueueRef.current);
      void flushTelemetry();
    },
    [flushTelemetry, language, nextEventSequenceNumber],
  );

  useEffect(() => {
    setApiTelemetryReporter((event) => {
      pushTelemetry(event);
    });
    return () => {
      setApiTelemetryReporter(null);
    };
  }, [pushTelemetry]);

  useEffect(() => {
    let cancelled = false;
    void refreshPublicConfig().then((config) => {
      if (!cancelled) {
        setPublicConfig(config);
      }
    });
    const onFocus = () => {
      void refreshPublicConfig();
    };
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void refreshPublicConfig();
      }
    };
    const interval = window.setInterval(() => {
      void refreshPublicConfig();
    }, 15000);
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [refreshPublicConfig]);

  useEffect(() => {
    const stored = readJson<StoredSessionState | null>(
      STORAGE_KEY,
      null,
    );
    if (stored?.demoSession && isDemoSession(stored.demoSession)) {
      setBraceletId(stored.braceletId ?? "");
      telemetryQueueRef.current = [];
      writeJson(TELEMETRY_KEY, telemetryQueueRef.current);
      commitSession(stored.demoSession);
      setIsHydrating(false);
      return;
    }

    if (!stored?.sessionId) {
      setIsHydrating(false);
      return;
    }

    let cancelled = false;
    resumeSession(stored.sessionId)
      .then((response) => {
        if (cancelled) {
          return;
        }
        setBraceletId(stored.braceletId ?? "");
        commitSession(response.session);
        pushTelemetry({
          event_type: "lifecycle",
          event_name: "resume_session",
          screen_name: response.session.screen,
          payload: {
            session_id: response.session.session_id,
          },
          client_context: currentClientContext(),
        });
        void flushTelemetry();
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        window.localStorage.removeItem(STORAGE_KEY);
      })
      .finally(() => {
        if (!cancelled) {
          setIsHydrating(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [commitSession, currentClientContext, flushTelemetry, pushTelemetry]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const onBeforeUnload = () =>
      pushTelemetry({
        event_type: "lifecycle",
        event_name: "page_reload",
        client_context: currentClientContext(),
      });
    const onOnline = () =>
      pushTelemetry({
        event_type: "network",
        event_name: "browser_online",
        client_context: currentClientContext(),
      });
    const onOffline = () =>
      pushTelemetry({
        event_type: "network",
        event_name: "browser_offline",
        client_context: currentClientContext(),
      });
    const onResize = () =>
      pushTelemetry({
        event_type: "viewport",
        event_name: "viewport_change",
        client_context: currentClientContext(),
      });
    const onOrientationChange = () =>
      pushTelemetry({
        event_type: "viewport",
        event_name: "orientation_change",
        client_context: currentClientContext(),
      });
    const onError = (event: ErrorEvent) =>
      pushTelemetry({
        event_type: "error",
        event_name: "js_error",
        error_name: event.error?.name ?? "Error",
        payload: {
          message: event.message,
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
        },
      });
    const onUnhandledRejection = (event: PromiseRejectionEvent) =>
      pushTelemetry({
        event_type: "error",
        event_name: "unhandled_rejection",
        error_name: "UnhandledRejection",
        payload: {
          reason:
            typeof event.reason === "string"
              ? event.reason
              : event.reason?.message ?? "Unhandled rejection",
        },
      });

    window.addEventListener("beforeunload", onBeforeUnload);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    window.addEventListener("resize", onResize);
    window.addEventListener("orientationchange", onOrientationChange);
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onUnhandledRejection);

    const connection = (
      navigator as Navigator & {
        connection?: EventTarget;
      }
    ).connection;
    const onConnectionChange = () =>
      pushTelemetry({
        event_type: "network",
        event_name: "connection_change",
        client_context: currentClientContext(),
      });
    connection?.addEventListener?.("change", onConnectionChange as EventListener);

    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("orientationchange", onOrientationChange);
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onUnhandledRejection);
      connection?.removeEventListener?.(
        "change",
        onConnectionChange as EventListener,
      );
    };
  }, [currentClientContext, pushTelemetry]);

  const startSession = useCallback(
    async (
      nextBraceletId: string,
      consents: ConsentPayload,
      metrics?: LandingMetrics,
    ): Promise<AccessResult> => {
      setIsLoading(true);
      try {
        const referral = readReferralParams();
        const demoScenario = getDemoScenario(
          publicConfigRef.current,
          nextBraceletId,
        );
        if (demoScenario) {
          const demoSession = buildDemoSession(
            publicConfigRef.current,
            language,
            nextBraceletId,
            demoScenario,
          );
          demoSession.language_at_access = language;
          demoSession.language_at_claim = language;
          demoSession.consent = {
            accepted:
              consents.participationAccepted &&
              consents.ageConfirmed &&
              consents.dataAccepted,
            age_confirmed: consents.ageConfirmed,
            info_accepted: consents.participationAccepted,
            data_accepted: consents.dataAccepted,
            accepted_at: new Date().toISOString(),
          };
          demoSession.client_context = toClientContextSummary(
            currentClientContext(),
          );
          demoSession.referral_source = referral.referralSource;
          demoSession.referral_medium = referral.referralMedium;
          demoSession.referral_campaign = referral.referralCampaign;
          demoSession.referral_link_id = referral.referralLinkId;
          demoSession.qr_entry_code = referral.qrEntryCode;
          demoSession.referral_landing_path = referral.referralPath;
          demoSession.consent_record = {
            language_at_access: language,
            landing_visible_ms: metrics?.landingVisibleMs ?? null,
            info_panels_opened: metrics?.infoPanelsOpened ?? [],
            info_panel_durations_ms: metrics?.infoPanelDurationsMs ?? {},
            checkbox_order: metrics?.checkboxOrder ?? [],
            checkbox_timestamps_ms: metrics?.checkboxTimestampsMs ?? {},
            continue_blocked_count: metrics?.continueBlockedCount ?? 0,
          };
          telemetryQueueRef.current = [];
          eventSequenceRef.current = 0;
          writeJson(TELEMETRY_KEY, telemetryQueueRef.current);
          writeNumber(EVENT_SEQUENCE_KEY, eventSequenceRef.current);
          setBraceletId(nextBraceletId);
          commitSession(demoSession);
          return { success: true, session: demoSession };
        }

        const response = await accessSession(
          nextBraceletId,
          consents.participationAccepted &&
            consents.ageConfirmed &&
            consents.dataAccepted,
          getInstallationId(),
          language,
          metrics?.landingVisibleMs,
          metrics?.infoPanelsOpened,
          metrics?.infoPanelDurationsMs,
          referral.referralCode,
          referral.referralSource,
          referral.referralMedium,
          referral.referralCampaign,
          referral.referralLinkId,
          referral.qrEntryCode,
          referral.referralPath,
          consents.ageConfirmed,
          consents.participationAccepted,
          consents.dataAccepted,
          metrics?.checkboxOrder,
          metrics?.checkboxTimestampsMs,
          metrics?.continueBlockedCount,
          currentClientContext(),
        );
        setBraceletId(nextBraceletId);
        commitSession(response.session);
        if (response.session.invited_by_referral_code) {
          pushTelemetry({
            event_type: "custom",
            event_name: "referral_session_started",
            screen_name: "landing",
            payload: {
              invited_by_referral_code: response.session.invited_by_referral_code,
              referral_source: response.session.referral_source,
            },
          });
        }
        pushTelemetry({
          event_type: "lifecycle",
          event_name: "session_started",
          screen_name: "landing",
          payload: {
            created_now: response.created_now,
            referral_source: referral.referralSource,
            referral_medium: referral.referralMedium,
            referral_campaign: referral.referralCampaign,
          },
          client_context: currentClientContext(),
        });
        await flushTelemetry();
        return { success: true, session: response.session };
      } catch (error) {
        if (error instanceof Error && isExperimentPausedError(error.message)) {
          await refreshPublicConfig();
        }
        pushTelemetry({
          event_type: "error",
          event_name: "access_error",
          payload: {
            message:
              error instanceof Error ? error.message : "No se pudo iniciar",
          },
        });
        if (error instanceof UserNotFoundError) {
          return { success: false, error: error.message, isNotFound: true };
        }
        return {
          success: false,
          error: error instanceof Error ? error.message : "No se pudo iniciar",
          isNotFound: false,
        };
      } finally {
        setIsLoading(false);
      }
    },
    [currentClientContext, flushTelemetry, language, pushTelemetry],
  );

  const moveToScreen = useCallback(async (screen: ScreenCursor) => {
    const current = sessionRef.current;
    if (!current) {
      return;
    }
    if (isDemoSession(current)) {
      commitSession({
        ...current,
        screen,
        state:
          screen === "game"
            ? "in_game"
            : screen === "report"
              ? "report_ready"
              : current.state,
      });
      return;
    }
    try {
      const response = await updateScreenCursor(current.session_id, screen);
      commitSession(response.session);
    } catch (error) {
      pushTelemetry({
        event_type: "error",
        event_name: "screen_update_error",
        payload: {
          screen,
          message: error instanceof Error ? error.message : "Error de cursor",
        },
      });
      if (error instanceof Error && isExperimentPausedError(error.message)) {
        await refreshPublicConfig();
      }
      throw error;
    }
  }, [commitSession, pushTelemetry, refreshPublicConfig]);

  const rollNext = useCallback(async (reactionMs?: number) => {
    const current = sessionRef.current;
    if (!current) {
      throw new Error("No hay sesion activa");
    }
    if (isDemoSession(current)) {
      const scenario = getDemoScenarioForSession(
        publicConfigRef.current,
        current,
        braceletId,
      );
      if (!scenario) {
        throw new Error("Accion no disponible");
      }
      const attemptIndex = current.throws.length + 1;
      const resultValue =
        scenario.throwSequence[current.throws.length % scenario.throwSequence.length];
      const nextThrows = [
        ...current.throws,
        {
          attempt_index: attemptIndex,
          result_value: resultValue,
          reaction_ms: reactionMs ?? null,
          delivered_at: new Date().toISOString(),
        },
      ];
      const firstResultValue = current.first_result_value ?? resultValue;
      commitSession({
        ...current,
        state: "in_game",
        screen: "game",
        throws: nextThrows,
        first_result_value: firstResultValue,
        last_seen_value: resultValue,
        max_seen_value: Math.max(current.max_seen_value ?? 0, resultValue),
        reroll_count: Math.max(0, nextThrows.length - 1),
        snapshot_record: buildDemoSnapshotRecord(current, {
          language_used: language,
          first_result_value: firstResultValue,
          last_seen_value: resultValue,
          all_values_seen: nextThrows.map((item) => item.result_value),
          rerolls_visible: nextThrows.slice(1).map((item) => item.result_value),
        }),
      });
      return resultValue;
    }
    const attemptIndex = current.throws.length + 1;
    try {
      const response = await rollSession(
        current.session_id,
        attemptIndex,
        reactionMs,
        makeIdempotencyKey("roll"),
      );
      commitSession(response.session);
      return response.attempt.result_value;
    } catch (error) {
      pushTelemetry({
        event_type: "error",
        event_name: "roll_error",
        screen_name: "game",
        payload: {
          attemptIndex,
          message: error instanceof Error ? error.message : "Error de tirada",
        },
      });
      if (error instanceof Error && isExperimentPausedError(error.message)) {
        await refreshPublicConfig();
      }
      throw error;
    }
  }, [braceletId, commitSession, language, pushTelemetry, refreshPublicConfig]);

  const prepareForReport = useCallback(async () => {
    const current = sessionRef.current;
    if (!current) {
      throw new Error("No hay sesion activa");
    }
    if (isDemoSession(current)) {
      const scenario = getDemoScenarioForSession(
        publicConfigRef.current,
        current,
        braceletId,
      );
      if (!scenario) {
        throw new Error("Accion no disponible");
      }
      const snapshot = buildDemoReportSnapshot(
        publicConfigRef.current,
        language,
        scenario,
      );
      commitSession({
        ...current,
        screen: "report",
        state: "report_ready",
        report_snapshot: snapshot,
        snapshot_record: buildDemoSnapshotRecord(current, {
          language_used: language,
          displayed_message_text: snapshot.message,
          control_message_text: snapshot.is_control
            ? snapshot.message
            : current.snapshot_record?.control_message_text ?? null,
          rerolls_visible: current.throws.slice(1).map((item) => item.result_value),
        }),
      });
      return;
    }
    try {
      const response = await prepareReport(
        current.session_id,
        makeIdempotencyKey("prepare"),
      );
      commitSession(response.session);
    } catch (error) {
      pushTelemetry({
        event_type: "error",
        event_name: "prepare_report_error",
        screen_name: "game",
        payload: {
          message:
            error instanceof Error ? error.message : "Error preparando reporte",
        },
      });
      if (error instanceof Error && isExperimentPausedError(error.message)) {
        await refreshPublicConfig();
      }
      throw error;
    }
  }, [braceletId, commitSession, language, pushTelemetry, refreshPublicConfig]);

  const submitClaim = useCallback(
    async (reportedValue: number, reactionMs?: number) => {
      const current = sessionRef.current;
      if (!current) {
        throw new Error("No hay sesion activa");
      }
      if (isDemoSession(current)) {
        const firstResult = current.first_result_value ?? reportedValue;
        const amountEur = current.selected_for_payment
          ? publicConfigRef.current.prize_eur[String(reportedValue)] ?? 0
          : 0;
        commitSession({
          ...current,
          screen: "exit",
          state: current.selected_for_payment
            ? "completed_win"
            : "completed_no_win",
          language_at_claim: language,
          is_valid_completed: true,
          valid_completed_at: new Date().toISOString(),
          claim: {
            reported_value: reportedValue,
            true_first_result: firstResult,
            is_honest: reportedValue === firstResult,
            matches_last_seen: reportedValue === current.last_seen_value,
            matches_any_seen: current.throws.some(
              (item) => item.result_value === reportedValue,
            ),
            submitted_at: new Date().toISOString(),
          },
          payment: {
            ...current.payment,
            eligible: current.selected_for_payment,
            amount_cents: amountEur * 100,
            amount_eur: amountEur,
            status: current.selected_for_payment ? "pending" : "not_eligible",
            reference_code: current.selected_for_payment
              ? current.payment.reference_code ?? `DEMO-${braceletId || "1234"}`
              : null,
          },
          snapshot_record: buildDemoSnapshotRecord(current, {
            language_used: language,
            final_state_shown: current.selected_for_payment ? "winner" : "loser",
          }),
        });
        return;
      }
      try {
        const response = await submitReport(
          current.session_id,
          reportedValue,
          reactionMs,
          makeIdempotencyKey("claim"),
          language,
        );
        commitSession(response.session);
        await flushTelemetry();
      } catch (error) {
        pushTelemetry({
          event_type: "error",
          event_name: "submit_claim_error",
          screen_name: "report",
          value: reportedValue,
          payload: {
            message:
              error instanceof Error ? error.message : "Error enviando reporte",
          },
        });
        if (error instanceof Error && isExperimentPausedError(error.message)) {
          await refreshPublicConfig();
        }
        throw error;
      }
    },
    [braceletId, commitSession, flushTelemetry, language, pushTelemetry, refreshPublicConfig],
  );

  const saveDisplaySnapshot = useCallback(
    async (payload: DisplaySnapshotRequest) => {
      const current = sessionRef.current;
      if (!current) {
        return;
      }
      if (isDemoSession(current)) {
        commitSession({
          ...current,
          snapshot_record: buildDemoSnapshotRecord(current, {
            language_used: payload.language ?? language,
            displayed_message_text: payload.treatment_message_text ?? null,
            control_message_text: payload.control_message_text ?? null,
            final_message_text: payload.final_message_text ?? null,
            payout_reference_shown: payload.payout_reference_shown ?? null,
            payout_phone_shown: payload.payout_phone_shown ?? null,
            rerolls_visible: payload.rerolls_visible,
            final_state_shown:
              current.snapshot_record?.final_state_shown ??
              (current.selected_for_payment ? "winner" : "loser"),
          }),
        });
        return;
      }
      try {
        await captureDisplaySnapshot(current.session_id, {
          ...payload,
          language: payload.language ?? language,
        });
      } catch (error) {
        pushTelemetry({
          event_type: "error",
          event_name: "display_snapshot_error",
          screen_name: payload.screen_name,
          payload: {
            message:
              error instanceof Error
                ? error.message
                : "Error guardando snapshot visible",
          },
        });
      }
    },
    [commitSession, language, pushTelemetry],
  );

  const lookupPaymentCode = useCallback(async (code: string) => {
    const current = sessionRef.current;
    const normalizedCode = code.trim().toUpperCase();
    if (
      current &&
      isDemoSession(current) &&
      current.selected_for_payment &&
      current.payment.reference_code?.toUpperCase() === normalizedCode
    ) {
      return {
        valid: true,
        status: "pending",
        amount_eur: current.payment.amount_eur,
        code: current.payment.reference_code,
        can_submit: true,
        donation_available: true,
        experiment_phase: current.experiment_phase,
      };
    }
    return paymentLookup(code);
  }, []);

  const submitPaymentRequest = useCallback(
    async (
      code: string,
      phone: string,
      donationRequested?: boolean,
      messageText?: string,
    ) => {
      const current = sessionRef.current;
      const normalizedCode = code.trim().toUpperCase();
      if (
        current &&
        isDemoSession(current) &&
        current.selected_for_payment &&
        current.payment.reference_code?.toUpperCase() === normalizedCode
      ) {
        commitSession({
          ...current,
          payment: {
            ...current.payment,
            status: "queued",
          },
          snapshot_record: buildDemoSnapshotRecord(current, {
            payout_phone_shown: phone,
          }),
        });
        return {
          ok: true,
          status: "queued",
          amount_eur: current.payment.amount_eur,
          requested_phone: phone,
          donation_requested: donationRequested ?? false,
        };
      }
      return paymentSubmit(code, phone, language, donationRequested, messageText);
    },
    [commitSession, language],
  );

  const submitInterestSignup = useCallback(
    async (email: string) => {
      return submitInterestSignupRequest(email, language);
    },
    [language],
  );

  const clearLocalSession = useCallback(() => {
    setSession(null);
    setBraceletId("");
    telemetryQueueRef.current = [];
    eventSequenceRef.current = 0;
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(STORAGE_KEY);
      window.localStorage.removeItem(TELEMETRY_KEY);
      window.localStorage.removeItem(EVENT_SEQUENCE_KEY);
    }
  }, []);

  const value = useMemo<SessionContextValue>(
      () => ({
        publicConfig,
        session,
        braceletId,
        isLoading,
      isHydrating,
      startSession,
      moveToScreen,
      rollNext,
      prepareForReport,
      submitClaim,
      saveDisplaySnapshot,
      lookupPaymentCode,
      submitPaymentRequest,
      submitInterestSignup,
      pushTelemetry,
      clearLocalSession,
    }),
      [
        publicConfig,
        session,
        braceletId,
        isLoading,
      isHydrating,
      startSession,
      moveToScreen,
      rollNext,
      prepareForReport,
      submitClaim,
      saveDisplaySnapshot,
      lookupPaymentCode,
      submitPaymentRequest,
      submitInterestSignup,
      pushTelemetry,
      clearLocalSession,
    ],
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used within SessionProvider");
  }
  return context;
}
