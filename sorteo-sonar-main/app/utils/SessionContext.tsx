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
  createReferralLink,
  DEFAULT_PUBLIC_CONFIG,
  fetchPublicConfig,
  OfflineError,
  paymentLookup,
  paymentSubmit,
  prepareReport,
  readCachedPublicConfig,
  resumeSession,
  rollSession,
  submitInterestSignup as submitInterestSignupRequest,
  submitReport,
  submitClaimFollowup as submitClaimFollowupRequest,
  updateScreenCursor,
  type PublicConfig,
  type ScreenCursor,
  type SessionPayload,
  type TelemetryEventRequest,
  type PaymentLookupResponse,
  type PaymentSubmitResponse,
  type InterestSignupResponse,
  type ClientContext,
  UserNotFoundError,
  writeCachedPublicConfig,
} from "./api";
import { collectClientContext } from "./clientContext";
import {
  initializeTelemetryQueue,
  queueTelemetryEvent,
  requestTelemetryFlush,
  resetTelemetryQueue,
} from "./telemetryQueue";
import {
  SUPPORTED_LANGUAGES,
  UI_LEXICON,
  type AppLanguage,
} from "./uiLexicon";

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

type RecoverableActionType = "roll" | "prepare_report" | "submit_claim";

type PendingActionState =
  | {
      type: "roll";
      sessionId: string;
      idempotencyKey: string;
      createdAt: number;
      retryCount: number;
      lastAttemptAt?: number;
      attemptIndex: number;
      reactionMs?: number;
    }
  | {
      type: "prepare_report";
      sessionId: string;
      idempotencyKey: string;
      createdAt: number;
      retryCount: number;
      lastAttemptAt?: number;
    }
  | {
      type: "submit_claim";
      sessionId: string;
      idempotencyKey: string;
      createdAt: number;
      retryCount: number;
      lastAttemptAt?: number;
      reportedValue: number;
      reactionMs?: number;
      language?: string;
    };

type StoredSessionState = {
  sessionId?: string;
  braceletId?: string;
  sessionSnapshot?: SessionPayload | null;
  pendingAction?: PendingActionState | null;
};

type NetworkRecoveryState = {
  phase: "idle" | "retrying";
  action: RecoverableActionType | null;
  message: string | null;
  retryCount: number;
};

type VisualTransitionPhase =
  | "idle"
  | "navigating"
  | "preparing_report"
  | "submitting_claim";

type VisualTransitionState = {
  phase: VisualTransitionPhase;
  sourceScreen: ScreenCursor | null;
  targetScreen: ScreenCursor | null;
};

type SessionRuntimeValue = {
  session: SessionPayload | null;
  displayScreen: ScreenCursor | null;
  isLoading: boolean;
  isHydrating: boolean;
  isOnline: boolean;
  networkRecovery: NetworkRecoveryState;
  visualTransition: VisualTransitionState;
};

export class DeferredRecoveryError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DeferredRecoveryError";
  }
}

type SessionActionsValue = {
  startSession: (
    braceletId: string,
    consents: ConsentPayload,
    metrics?: LandingMetrics,
  ) => Promise<AccessResult>;
  moveToScreen: (screen: ScreenCursor) => Promise<void>;
  rollNext: (reactionMs?: number) => Promise<number>;
  prepareForReport: () => Promise<void>;
  submitClaim: (reportedValue: number, reactionMs?: number) => Promise<void>;
  submitClaimFollowup: (payload: {
    crowd_prediction_value?: number;
    social_recall_count?: number;
  }) => Promise<void>;
  lookupPaymentCode: (code: string) => Promise<PaymentLookupResponse>;
  submitPaymentRequest: (
    code: string,
    braceletId: string,
    phone: string,
    donationRequested?: boolean,
    messageText?: string,
  ) => Promise<PaymentSubmitResponse>;
  submitInterestSignup: (email: string) => Promise<InterestSignupResponse>;
  createReferralInviteLink: (options?: {
    channel?: string;
    trafficSource?: string;
    trafficMedium?: string;
    campaignCode?: string;
    targetPath?: string;
  }) => Promise<string>;
  pushTelemetry: (event: TelemetryEventRequest) => void;
  clearLocalSession: () => void;
};

type SessionContextValue = SessionRuntimeValue &
  SessionActionsValue & {
    publicConfig: PublicConfig;
  };

const PublicConfigContext = createContext<PublicConfig | undefined>(undefined);
const SessionRuntimeContext = createContext<SessionRuntimeValue | undefined>(
  undefined,
);
const SessionActionsContext = createContext<SessionActionsValue | undefined>(
  undefined,
);

const STORAGE_KEY = "sonar_session_v2";
const INSTALLATION_KEY = "sonar_installation_v1";
const LANGUAGE_STORAGE_KEY = "sonar_language_v1";
const CONFIG_REFRESH_INTERVAL_MS = 60000;
const CONFIG_REFRESH_MIN_GAP_MS = 20000;
const CRITICAL_REQUEST_TIMEOUT_MS = 3500;
const RECOVERY_RETRY_DELAYS_MS = [350, 900] as const;
const BACKGROUND_RECOVERY_RETRY_MS = 5000;
const MINIMAL_TELEMETRY_EVENT_NAMES = new Set([
  "session_start",
  "first_throw",
  "reroll_count",
  "report_value",
  "reaction_time_ms",
  "session_end",
]);

const IDLE_NETWORK_RECOVERY: NetworkRecoveryState = {
  phase: "idle",
  action: null,
  message: null,
  retryCount: 0,
};

const IDLE_VISUAL_TRANSITION: VisualTransitionState = {
  phase: "idle",
  sourceScreen: null,
  targetScreen: null,
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

function serializePublicConfig(config: PublicConfig) {
  return JSON.stringify(config);
}

function readStoredLanguage(): AppLanguage {
  if (typeof window === "undefined") {
    return "es";
  }
  const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (stored && SUPPORTED_LANGUAGES.includes(stored as AppLanguage)) {
    return stored as AppLanguage;
  }
  return "es";
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

function delay(ms: number) {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function withRequestTimeout<T>(
  request: (init?: RequestInit) => Promise<T>,
  timeoutMs = CRITICAL_REQUEST_TIMEOUT_MS,
) {
  if (typeof AbortController === "undefined") {
    return request();
  }
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => {
    controller.abort("timeout");
  }, timeoutMs);
  return request({ signal: controller.signal }).finally(() => {
    window.clearTimeout(timeoutId);
  });
}

function isTransientNetworkError(error: unknown) {
  if (error instanceof OfflineError) {
    return true;
  }
  if (error instanceof UserNotFoundError) {
    return false;
  }
  if (typeof DOMException !== "undefined" && error instanceof DOMException) {
    return error.name === "AbortError";
  }
  const message =
    error instanceof Error ? error.message.toLowerCase() : String(error).toLowerCase();
  return (
    message.includes("failed to fetch") ||
    message.includes("networkerror") ||
    message.includes("load failed") ||
    message.includes("network request failed") ||
    message.includes("network error") ||
    message.includes("timeout") ||
    message.includes("aborterror") ||
    message.includes("signal is aborted")
  );
}

function hasPendingActionBeenApplied(
  session: SessionPayload,
  pendingAction: PendingActionState,
) {
  switch (pendingAction.type) {
    case "roll":
      return session.throws.some(
        (item) => item.attempt_index === pendingAction.attemptIndex,
      );
    case "prepare_report":
      return Boolean(session.report_snapshot);
    case "submit_claim":
      return Boolean(session.claim);
  }
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
    referralLinkId:
      url.searchParams.get("ref_id") ??
      url.searchParams.get("link_id") ??
      qrEntryCode,
    qrEntryCode,
    referralPath: `${url.pathname}${url.search}`,
  };
}

function isExperimentPausedError(message: string) {
  return /temporalmente detenido/i.test(message);
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [publicConfig, setPublicConfig] = useState<PublicConfig>(
    () => readCachedPublicConfig() ?? DEFAULT_PUBLIC_CONFIG,
  );
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isHydrating, setIsHydrating] = useState(true);
  const [isOnline, setIsOnline] = useState(
    () => typeof navigator === "undefined" || navigator.onLine,
  );
  const [pendingAction, setPendingAction] = useState<PendingActionState | null>(
    null,
  );
  const [networkRecovery, setNetworkRecovery] =
    useState<NetworkRecoveryState>(IDLE_NETWORK_RECOVERY);
  const [visualTransition, setVisualTransition] =
    useState<VisualTransitionState>(IDLE_VISUAL_TRANSITION);

  const initialPublicConfig = readCachedPublicConfig() ?? DEFAULT_PUBLIC_CONFIG;
  const languageRef = useRef<AppLanguage>(readStoredLanguage());
  const braceletIdRef = useRef("");
  const publicConfigRef = useRef<PublicConfig>(initialPublicConfig);
  const publicConfigSignatureRef = useRef(
    serializePublicConfig(initialPublicConfig),
  );
  const configRefreshInFlightRef = useRef<Promise<PublicConfig> | null>(null);
  const lastConfigRefreshAtRef = useRef(0);
  const sessionRef = useRef<SessionPayload | null>(null);
  const eventSequenceRef = useRef<number>(0);
  const pendingActionRef = useRef<PendingActionState | null>(null);
  const recoveryExecutionKeyRef = useRef<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const syncStoredLanguage = () => {
      languageRef.current = readStoredLanguage();
    };

    const onLanguageChanged = (event: Event) => {
      const nextLanguage = (event as CustomEvent<{ language?: string }>).detail
        ?.language;
      if (nextLanguage && SUPPORTED_LANGUAGES.includes(nextLanguage as AppLanguage)) {
        languageRef.current = nextLanguage as AppLanguage;
        return;
      }
      syncStoredLanguage();
    };

    const onStorage = (event: StorageEvent) => {
      if (event.key === LANGUAGE_STORAGE_KEY) {
        syncStoredLanguage();
      }
    };

    syncStoredLanguage();
    window.addEventListener(
      "sonar_language_changed",
      onLanguageChanged as EventListener,
    );
    window.addEventListener("storage", onStorage);

    return () => {
      window.removeEventListener(
        "sonar_language_changed",
        onLanguageChanged as EventListener,
      );
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const syncOnlineState = () => {
      setIsOnline(window.navigator.onLine);
    };
    syncOnlineState();
    window.addEventListener("online", syncOnlineState);
    window.addEventListener("offline", syncOnlineState);
    return () => {
      window.removeEventListener("online", syncOnlineState);
      window.removeEventListener("offline", syncOnlineState);
    };
  }, []);

  useEffect(() => {
    initializeTelemetryQueue();
  }, []);

  const getReconnectMessage = useCallback(
    () => UI_LEXICON[languageRef.current].common.reconnecting,
    [],
  );

  const setPendingActionState = useCallback((nextPending: PendingActionState | null) => {
    pendingActionRef.current = nextPending;
    setPendingAction(nextPending);
    if (!nextPending) {
      recoveryExecutionKeyRef.current = null;
    }
  }, []);

  const markNetworkRecovery = useCallback(
    (action: RecoverableActionType, retryCount: number) => {
      setNetworkRecovery({
        phase: "retrying",
        action,
        message: getReconnectMessage(),
        retryCount,
      });
    },
    [getReconnectMessage],
  );

  const clearNetworkRecovery = useCallback(() => {
    setNetworkRecovery(IDLE_NETWORK_RECOVERY);
  }, []);

  const beginVisualTransition = useCallback(
    (
      phase: Exclude<VisualTransitionPhase, "idle">,
      targetScreen: ScreenCursor,
    ) => {
      setVisualTransition({
        phase,
        sourceScreen: sessionRef.current?.screen ?? null,
        targetScreen,
      });
    },
    [],
  );

  const clearVisualTransition = useCallback(() => {
    setVisualTransition((current) =>
      current.phase === "idle" ? current : IDLE_VISUAL_TRANSITION,
    );
  }, []);

  const commitSession = useCallback((nextSession: SessionPayload | null) => {
    sessionRef.current = nextSession;
    setSession(nextSession);
  }, []);

  const commitPublicConfig = useCallback((nextConfig: PublicConfig) => {
    const nextSignature = serializePublicConfig(nextConfig);
    lastConfigRefreshAtRef.current = Date.now();
    if (nextSignature === publicConfigSignatureRef.current) {
      writeCachedPublicConfig(nextConfig);
      return publicConfigRef.current;
    }
    publicConfigSignatureRef.current = nextSignature;
    publicConfigRef.current = nextConfig;
    writeCachedPublicConfig(nextConfig);
    setPublicConfig(nextConfig);
    return nextConfig;
  }, []);

  const getCurrentLanguage = useCallback(() => languageRef.current, []);

  const refreshPublicConfig = useCallback(async (force = false) => {
    const now = Date.now();
    if (!force) {
      if (configRefreshInFlightRef.current) {
        return configRefreshInFlightRef.current;
      }
      if (now - lastConfigRefreshAtRef.current < CONFIG_REFRESH_MIN_GAP_MS) {
        return publicConfigRef.current;
      }
    }

    const refreshPromise = (async () => {
      try {
        const nextConfig = await fetchPublicConfig();
        return commitPublicConfig(nextConfig);
      } catch {
        return publicConfigRef.current;
      } finally {
        configRefreshInFlightRef.current = null;
      }
    })();

    configRefreshInFlightRef.current = refreshPromise;
    return refreshPromise;
  }, [commitPublicConfig]);

  useEffect(() => {
    sessionRef.current = session;
    if (typeof window === "undefined") {
      return;
    }
    if (!session) {
      if (!pendingAction) {
        window.localStorage.removeItem(STORAGE_KEY);
      }
      return;
    }
    const storedSession: StoredSessionState = {
      sessionId: session.session_id,
      braceletId: braceletIdRef.current,
      sessionSnapshot: session,
      pendingAction,
    };
    writeJson(STORAGE_KEY, storedSession);
    const maxKnownSequence = session.session_metrics?.max_event_sequence_number ?? 0;
    if (maxKnownSequence > eventSequenceRef.current) {
      eventSequenceRef.current = maxKnownSequence;
    }
  }, [pendingAction, session]);

  useEffect(() => {
    if (!session) {
      setVisualTransition((current) =>
        current.phase === "idle" ? current : IDLE_VISUAL_TRANSITION,
      );
      return;
    }
    setVisualTransition((current) => {
      if (current.phase === "idle") {
        return current;
      }
      if (session.screen === current.targetScreen) {
        return IDLE_VISUAL_TRANSITION;
      }
      if (current.phase === "preparing_report" && session.report_snapshot) {
        return IDLE_VISUAL_TRANSITION;
      }
      if (current.phase === "submitting_claim" && session.claim) {
        return IDLE_VISUAL_TRANSITION;
      }
      return current;
    });
  }, [session]);

  const nextEventSequenceNumber = useCallback(() => {
    eventSequenceRef.current += 1;
    return eventSequenceRef.current;
  }, []);

  const currentClientContext = useCallback(
    (extras?: Partial<ClientContext>) =>
      collectClientContext(getCurrentLanguage(), extras),
    [getCurrentLanguage],
  );

  const enqueueMinimalTelemetry = useCallback(
    (
      sessionId: string | null | undefined,
      eventName: string,
      extras?: {
        value?: number;
        durationMs?: number;
      },
    ) => {
      if (!sessionId || !MINIMAL_TELEMETRY_EVENT_NAMES.has(eventName)) {
        return;
      }
      queueTelemetryEvent(sessionId, {
        event_type: "experiment",
        event_name: eventName,
        client_ts: Date.now(),
        event_sequence_number: nextEventSequenceNumber(),
        value: extras?.value,
        duration_ms: extras?.durationMs,
      });
    },
    [nextEventSequenceNumber],
  );

  const pushTelemetry = useCallback(
    (event: TelemetryEventRequest) => {
      const currentSession = sessionRef.current;
      if (
        !currentSession ||
        !MINIMAL_TELEMETRY_EVENT_NAMES.has(event.event_name)
      ) {
        return;
      }
      queueTelemetryEvent(currentSession.session_id, {
        event_type: "experiment",
        event_name: event.event_name,
        client_ts: event.client_ts ?? Date.now(),
        duration_ms: event.duration_ms,
        value: event.value,
        event_sequence_number:
          event.event_sequence_number ?? nextEventSequenceNumber(),
      });
    },
    [nextEventSequenceNumber],
  );

  useEffect(() => {
    void refreshPublicConfig(true);
    const onFocus = () => {
      void refreshPublicConfig();
    };
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void refreshPublicConfig();
      }
    };
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void refreshPublicConfig();
      }
    }, CONFIG_REFRESH_INTERVAL_MS);
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
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
    setPendingActionState(stored?.pendingAction ?? null);
    braceletIdRef.current = stored?.braceletId ?? "";
    if (stored?.sessionSnapshot) {
      commitSession(stored.sessionSnapshot);
    }
    if (!stored?.sessionId) {
      setIsHydrating(false);
      return;
    }
    if (typeof navigator !== "undefined" && navigator.onLine === false) {
      if (stored.pendingAction) {
        markNetworkRecovery(
          stored.pendingAction.type,
          stored.pendingAction.retryCount,
        );
      }
      setIsHydrating(false);
      return;
    }

    let cancelled = false;
    resumeSession(stored.sessionId)
      .then((response) => {
        if (cancelled) {
          return;
        }
        clearNetworkRecovery();
        commitSession(response.session);
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        if (error instanceof UserNotFoundError) {
          commitSession(null);
          setPendingActionState(null);
          window.localStorage.removeItem(STORAGE_KEY);
          return;
        }
        if (stored?.pendingAction) {
          markNetworkRecovery(
            stored.pendingAction.type,
            stored.pendingAction.retryCount,
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsHydrating(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [
    clearNetworkRecovery,
    commitSession,
    markNetworkRecovery,
    setPendingActionState,
  ]);

  const runRecoverableAction = useCallback(
    function runRecoverableActionInternal<T>(
      pending: PendingActionState,
      request: (init?: RequestInit) => Promise<T>,
      onSuccess: (response: T) => void | Promise<void>,
    ) {
      return (async () => {
        const reconnectMessage = getReconnectMessage();
        for (
          let attempt = 0;
          attempt <= RECOVERY_RETRY_DELAYS_MS.length;
          attempt += 1
        ) {
          setPendingActionState({
            ...pending,
            retryCount: attempt,
            lastAttemptAt: Date.now(),
          });
          if (attempt > 0) {
            markNetworkRecovery(pending.type, attempt);
          }
          try {
            const response = await withRequestTimeout(request);
            clearNetworkRecovery();
            setPendingActionState(null);
            await onSuccess(response);
            return response;
          } catch (error) {
            if (error instanceof Error && isExperimentPausedError(error.message)) {
              await refreshPublicConfig(true);
            }
            if (!isTransientNetworkError(error)) {
              clearNetworkRecovery();
              setPendingActionState(null);
              throw error;
            }
            markNetworkRecovery(pending.type, attempt + 1);
            if (attempt < RECOVERY_RETRY_DELAYS_MS.length) {
              await delay(RECOVERY_RETRY_DELAYS_MS[attempt]);
              continue;
            }
            throw new DeferredRecoveryError(reconnectMessage);
          }
        }
        throw new DeferredRecoveryError(reconnectMessage);
      })();
    },
    [
      clearNetworkRecovery,
      getReconnectMessage,
      markNetworkRecovery,
      refreshPublicConfig,
      setPendingActionState,
    ],
  );

  const executeRollPendingAction = useCallback(
    async (pending: Extract<PendingActionState, { type: "roll" }>) => {
      const current = sessionRef.current;
      if (!current || current.session_id !== pending.sessionId) {
        throw new Error("No hay sesion activa");
      }
      if (hasPendingActionBeenApplied(current, pending)) {
        clearNetworkRecovery();
        setPendingActionState(null);
        return (
          current.throws.find((item) => item.attempt_index === pending.attemptIndex)
            ?.result_value ??
          current.last_seen_value ??
          current.first_result_value ??
          0
        );
      }
      const response = await runRecoverableAction(
        pending,
        (init) =>
          rollSession(
            current.session_id,
            pending.attemptIndex,
            pending.reactionMs,
            pending.idempotencyKey,
            init,
          ),
        (result) => {
          commitSession(result.session);
          if (pending.attemptIndex === 1) {
            enqueueMinimalTelemetry(result.session.session_id, "first_throw", {
              value: result.attempt.result_value,
            });
          }
        },
      );
      return response.attempt.result_value;
    },
    [
      clearNetworkRecovery,
      commitSession,
      enqueueMinimalTelemetry,
      runRecoverableAction,
      setPendingActionState,
    ],
  );

  const executePrepareReportPendingAction = useCallback(
    async (pending: Extract<PendingActionState, { type: "prepare_report" }>) => {
      const current = sessionRef.current;
      if (!current || current.session_id !== pending.sessionId) {
        throw new Error("No hay sesion activa");
      }
      if (hasPendingActionBeenApplied(current, pending)) {
        clearNetworkRecovery();
        setPendingActionState(null);
        return;
      }
      await runRecoverableAction(
        pending,
        (init) => prepareReport(current.session_id, pending.idempotencyKey, init),
        (result) => {
          commitSession(result.session);
        },
      );
    },
    [clearNetworkRecovery, commitSession, runRecoverableAction, setPendingActionState],
  );

  const executeSubmitClaimPendingAction = useCallback(
    async (pending: Extract<PendingActionState, { type: "submit_claim" }>) => {
      const current = sessionRef.current;
      if (!current || current.session_id !== pending.sessionId) {
        throw new Error("No hay sesion activa");
      }
      if (hasPendingActionBeenApplied(current, pending)) {
        clearNetworkRecovery();
        setPendingActionState(null);
        return;
      }
      const response = await runRecoverableAction(
        pending,
        (init) =>
          submitReport(
            current.session_id,
            pending.reportedValue,
            pending.reactionMs,
            pending.idempotencyKey,
            pending.language,
            init,
          ),
        (result) => {
          commitSession(result.session);
          enqueueMinimalTelemetry(result.session.session_id, "reroll_count", {
            value: result.session.reroll_count,
          });
          enqueueMinimalTelemetry(result.session.session_id, "report_value", {
            value: result.session.claim?.reported_value ?? pending.reportedValue,
          });
          if (typeof pending.reactionMs === "number") {
            enqueueMinimalTelemetry(result.session.session_id, "reaction_time_ms", {
              durationMs: pending.reactionMs,
            });
          }
          enqueueMinimalTelemetry(result.session.session_id, "session_end");
          requestTelemetryFlush({ immediate: true, keepalive: true });
        },
      );
      return response;
    },
    [
      clearNetworkRecovery,
      commitSession,
      enqueueMinimalTelemetry,
      runRecoverableAction,
      setPendingActionState,
    ],
  );

  const resumePendingAction = useCallback(async () => {
    const pending = pendingActionRef.current;
    const current = sessionRef.current;
    if (!pending || !current) {
      return;
    }
    if (pending.sessionId !== current.session_id) {
      setPendingActionState(null);
      clearNetworkRecovery();
      return;
    }
    if (hasPendingActionBeenApplied(current, pending)) {
      setPendingActionState(null);
      clearNetworkRecovery();
      return;
    }
    if (recoveryExecutionKeyRef.current === pending.idempotencyKey) {
      return;
    }
    recoveryExecutionKeyRef.current = pending.idempotencyKey;
    try {
      if (pending.type === "roll") {
        await executeRollPendingAction(pending);
      } else if (pending.type === "prepare_report") {
        await executePrepareReportPendingAction(pending);
      } else {
        await executeSubmitClaimPendingAction(pending);
      }
    } catch (error) {
      if (!(error instanceof DeferredRecoveryError)) {
        throw error;
      }
    } finally {
      if (recoveryExecutionKeyRef.current === pending.idempotencyKey) {
        recoveryExecutionKeyRef.current = null;
      }
    }
  }, [
    clearNetworkRecovery,
    executePrepareReportPendingAction,
    executeRollPendingAction,
    executeSubmitClaimPendingAction,
    setPendingActionState,
  ]);

  useEffect(() => {
    if (!pendingAction || isHydrating) {
      return;
    }
    const timer = window.setTimeout(() => {
      void resumePendingAction().catch(() => {
        // Keep the user on the current screen; a fresh retry will be scheduled.
      });
    }, BACKGROUND_RECOVERY_RETRY_MS);
    return () => {
      window.clearTimeout(timer);
    };
  }, [isHydrating, pendingAction, resumePendingAction]);

  useEffect(() => {
    const onOnline = () => {
      void resumePendingAction().catch(() => {
        // The session remains persisted locally for the next retry opportunity.
      });
    };
    window.addEventListener("online", onOnline);
    return () => {
      window.removeEventListener("online", onOnline);
    };
  }, [resumePendingAction]);

  useEffect(() => {
    if (!pendingAction || !session) {
      return;
    }
    if (pendingAction.sessionId !== session.session_id) {
      setPendingActionState(null);
      clearNetworkRecovery();
      return;
    }
    if (hasPendingActionBeenApplied(session, pendingAction)) {
      setPendingActionState(null);
      clearNetworkRecovery();
    }
  }, [clearNetworkRecovery, pendingAction, session, setPendingActionState]);

  const startSession = useCallback(
    async (
      nextBraceletId: string,
      consents: ConsentPayload,
      metrics?: LandingMetrics,
    ): Promise<AccessResult> => {
      const currentLanguage = getCurrentLanguage();
      setIsLoading(true);
      try {
        const referral = readReferralParams();
        const response = await accessSession(
          nextBraceletId,
          consents.participationAccepted &&
            consents.ageConfirmed &&
            consents.dataAccepted,
          getInstallationId(),
          currentLanguage,
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
        resetTelemetryQueue();
        eventSequenceRef.current = 0;
        braceletIdRef.current = nextBraceletId;
        setPendingActionState(null);
        clearNetworkRecovery();
        clearVisualTransition();
        commitSession(response.session);
        enqueueMinimalTelemetry(response.session.session_id, "session_start");
        return { success: true, session: response.session };
      } catch (error) {
        if (error instanceof Error && isExperimentPausedError(error.message)) {
          await refreshPublicConfig(true);
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
        if (error instanceof OfflineError) {
          return {
            success: false,
            error: UI_LEXICON[currentLanguage].common.offlineStartError,
            isNotFound: false,
          };
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
    [
      clearNetworkRecovery,
      clearVisualTransition,
      currentClientContext,
      enqueueMinimalTelemetry,
      getCurrentLanguage,
      pushTelemetry,
      refreshPublicConfig,
      setPendingActionState,
    ],
  );

  const moveToScreen = useCallback(async (screen: ScreenCursor) => {
    const current = sessionRef.current;
    if (!current) {
      return;
    }
    if (current.screen === screen) {
      clearVisualTransition();
      return;
    }
    beginVisualTransition("navigating", screen);
    try {
      const response = await withRequestTimeout((init) =>
        updateScreenCursor(current.session_id, screen, init),
      );
      commitSession(response.session);
      clearVisualTransition();
    } catch (error) {
      clearVisualTransition();
      pushTelemetry({
        event_type: "error",
        event_name: "screen_update_error",
        payload: {
          screen,
          message: error instanceof Error ? error.message : "Error de cursor",
        },
      });
      if (error instanceof Error && isExperimentPausedError(error.message)) {
        await refreshPublicConfig(true);
      }
      throw error;
    }
  }, [
    beginVisualTransition,
    clearVisualTransition,
    commitSession,
    pushTelemetry,
    refreshPublicConfig,
  ]);

  const rollNext = useCallback(async (reactionMs?: number) => {
    const current = sessionRef.current;
    if (!current) {
      throw new Error("No hay sesion activa");
    }
    const existingPending = pendingActionRef.current;
    if (
      existingPending?.type === "roll" &&
      existingPending.sessionId === current.session_id
    ) {
      if (recoveryExecutionKeyRef.current === existingPending.idempotencyKey) {
        throw new DeferredRecoveryError(getReconnectMessage());
      }
      return executeRollPendingAction(existingPending);
    }
    const attemptIndex = current.throws.length + 1;
    const pending: Extract<PendingActionState, { type: "roll" }> = {
      type: "roll",
      sessionId: current.session_id,
      idempotencyKey: makeIdempotencyKey("roll"),
      createdAt: Date.now(),
      retryCount: 0,
      attemptIndex,
      reactionMs,
    };
    try {
      return await executeRollPendingAction(pending);
    } catch (error) {
      if (error instanceof DeferredRecoveryError) {
        throw error;
      }
      pushTelemetry({
        event_type: "error",
        event_name: "roll_error",
        screen_name: "game",
        payload: {
          attemptIndex,
          message: error instanceof Error ? error.message : "Error de tirada",
        },
      });
      throw error;
    }
  }, [
    commitSession,
    executeRollPendingAction,
    getCurrentLanguage,
    getReconnectMessage,
    pushTelemetry,
  ]);

  const prepareForReport = useCallback(async () => {
    const current = sessionRef.current;
    if (!current) {
      throw new Error("No hay sesion activa");
    }
    beginVisualTransition("preparing_report", "report");
    const existingPending = pendingActionRef.current;
    if (
      existingPending?.type === "prepare_report" &&
      existingPending.sessionId === current.session_id
    ) {
      if (recoveryExecutionKeyRef.current === existingPending.idempotencyKey) {
        throw new DeferredRecoveryError(getReconnectMessage());
      }
      return executePrepareReportPendingAction(existingPending);
    }
    const pending: Extract<PendingActionState, { type: "prepare_report" }> = {
      type: "prepare_report",
      sessionId: current.session_id,
      idempotencyKey: makeIdempotencyKey("prepare"),
      createdAt: Date.now(),
      retryCount: 0,
    };
    try {
      await executePrepareReportPendingAction(pending);
      clearVisualTransition();
    } catch (error) {
      if (error instanceof DeferredRecoveryError) {
        throw error;
      }
      clearVisualTransition();
      pushTelemetry({
        event_type: "error",
        event_name: "prepare_report_error",
        screen_name: "game",
        payload: {
          message:
            error instanceof Error ? error.message : "Error preparando reporte",
        },
      });
      throw error;
    }
  }, [
    beginVisualTransition,
    clearVisualTransition,
    commitSession,
    executePrepareReportPendingAction,
    getCurrentLanguage,
    getReconnectMessage,
    pushTelemetry,
  ]);

  const submitClaim = useCallback(
    async (reportedValue: number, reactionMs?: number) => {
      const current = sessionRef.current;
      if (!current) {
        throw new Error("No hay sesion activa");
      }
      beginVisualTransition("submitting_claim", "exit");
      const existingPending = pendingActionRef.current;
      if (
        existingPending?.type === "submit_claim" &&
        existingPending.sessionId === current.session_id
      ) {
        if (recoveryExecutionKeyRef.current === existingPending.idempotencyKey) {
          throw new DeferredRecoveryError(getReconnectMessage());
        }
        await executeSubmitClaimPendingAction(existingPending);
        return;
      }

      try {
        const currentLanguage = getCurrentLanguage();
        const pending: Extract<PendingActionState, { type: "submit_claim" }> = {
          type: "submit_claim",
          sessionId: current.session_id,
          idempotencyKey: makeIdempotencyKey("claim"),
          createdAt: Date.now(),
          retryCount: 0,
          reportedValue,
          reactionMs,
          language: currentLanguage,
        };
        await executeSubmitClaimPendingAction(pending);
        clearVisualTransition();
      } catch (error) {
        if (error instanceof DeferredRecoveryError) {
          throw error;
        }
        clearVisualTransition();
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
        throw error;
      }
    },
    [
      beginVisualTransition,
      clearVisualTransition,
      commitSession,
      executeSubmitClaimPendingAction,
      getCurrentLanguage,
      getReconnectMessage,
      pushTelemetry,
    ],
  );

  const submitClaimFollowup = useCallback(
    async (payload: { crowd_prediction_value?: number; social_recall_count?: number }) => {
      const current = sessionRef.current;
      if (!current) {
        throw new Error("No hay sesiÃ³n disponible");
      }
      const currentLanguage = getCurrentLanguage();
      if (!current.claim) {
        throw new Error("La sesiÃ³n todavÃ­a no tiene claim");
      }
      try {
        const response = await submitClaimFollowupRequest(current.session_id, {
          ...payload,
          language: currentLanguage,
        });
        commitSession(response.session);
      } catch (error) {
        pushTelemetry({
          event_type: "error",
          event_name: "claim_followup_error",
          screen_name: "exit",
          payload: {
            message:
              error instanceof Error ? error.message : "Error guardando respuestas finales",
            ...payload,
          },
        });
        if (error instanceof Error && isExperimentPausedError(error.message)) {
          await refreshPublicConfig(true);
        }
        throw error;
      }
    },
    [commitSession, getCurrentLanguage, pushTelemetry, refreshPublicConfig],
  );

  const lookupPaymentCode = useCallback(async (code: string) => {
    return paymentLookup(code);
  }, []);

  const submitPaymentRequest = useCallback(
    async (
      code: string,
      submittedBraceletId: string,
      phone: string,
      donationRequested?: boolean,
      messageText?: string,
    ) => {
      return paymentSubmit(
        code,
        submittedBraceletId,
        phone,
        getCurrentLanguage(),
        donationRequested,
        messageText,
      );
    },
    [commitSession, getCurrentLanguage],
  );

  const submitInterestSignup = useCallback(
    async (email: string) => {
      return submitInterestSignupRequest(email, getCurrentLanguage());
    },
    [getCurrentLanguage],
  );

  const createReferralInviteLink = useCallback(
    async (options?: {
      channel?: string;
      trafficSource?: string;
      trafficMedium?: string;
      campaignCode?: string;
      targetPath?: string;
    }) => {
      const current = sessionRef.current;
      if (!current) {
        throw new Error("No hay sesion activa");
      }
      const link = await createReferralLink(current.session_id, options);
      return link.share_url;
    },
    [],
  );

  const clearLocalSession = useCallback(() => {
    const currentSessionId = sessionRef.current?.session_id ?? null;
    commitSession(null);
    setPendingActionState(null);
    clearNetworkRecovery();
    clearVisualTransition();
    braceletIdRef.current = "";
    resetTelemetryQueue(currentSessionId);
    eventSequenceRef.current = 0;
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }, [
    clearNetworkRecovery,
    clearVisualTransition,
    commitSession,
    setPendingActionState,
  ]);

  const runtimeValue = useMemo<SessionRuntimeValue>(
    () => ({
      session,
      displayScreen: visualTransition.targetScreen ?? session?.screen ?? null,
      isLoading,
      isHydrating,
      isOnline,
      networkRecovery,
      visualTransition,
    }),
    [
      isHydrating,
      isLoading,
      isOnline,
      networkRecovery,
      session,
      visualTransition,
    ],
  );

  const actionsValue = useMemo<SessionActionsValue>(
    () => ({
      startSession,
      moveToScreen,
      rollNext,
      prepareForReport,
      submitClaim,
      submitClaimFollowup,
      lookupPaymentCode,
      submitPaymentRequest,
      submitInterestSignup,
      createReferralInviteLink,
      pushTelemetry,
      clearLocalSession,
    }),
    [
      startSession,
      moveToScreen,
      rollNext,
      prepareForReport,
      submitClaim,
      submitClaimFollowup,
      lookupPaymentCode,
      submitPaymentRequest,
      submitInterestSignup,
      createReferralInviteLink,
      pushTelemetry,
      clearLocalSession,
    ],
  );

  return (
    <PublicConfigContext.Provider value={publicConfig}>
      <SessionRuntimeContext.Provider value={runtimeValue}>
        <SessionActionsContext.Provider value={actionsValue}>
          {children}
        </SessionActionsContext.Provider>
      </SessionRuntimeContext.Provider>
    </PublicConfigContext.Provider>
  );
}

export function usePublicConfig() {
  const context = useContext(PublicConfigContext);
  if (!context) {
    throw new Error("usePublicConfig must be used within SessionProvider");
  }
  return context;
}

export function useSessionRuntime() {
  const context = useContext(SessionRuntimeContext);
  if (!context) {
    throw new Error("useSessionRuntime must be used within SessionProvider");
  }
  return context;
}

export function useSessionActions() {
  const context = useContext(SessionActionsContext);
  if (!context) {
    throw new Error("useSessionActions must be used within SessionProvider");
  }
  return context;
}

export function useSession() {
  const publicConfig = usePublicConfig();
  const runtime = useSessionRuntime();
  const actions = useSessionActions();
  return useMemo<SessionContextValue>(
    () => ({
      publicConfig,
      ...runtime,
      ...actions,
    }),
    [publicConfig, runtime, actions],
  );
}

