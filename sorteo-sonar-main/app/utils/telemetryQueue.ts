import {
  postTelemetryBatch,
  type TelemetryEventRequest,
} from "./api";

const TELEMETRY_FLUSH_INTERVAL_MS = 5000;
const TELEMETRY_BATCH_SIZE = 12;
const TELEMETRY_MAX_EVENTS_PER_SESSION = 12;
const TELEMETRY_RETRY_BASE_MS = 3000;
const TELEMETRY_RETRY_MAX_MS = 30000;

type FlushOptions = {
  immediate?: boolean;
  keepalive?: boolean;
};

type TelemetryQueueMap = Map<string, TelemetryEventRequest[]>;

const queuedEventsBySession: TelemetryQueueMap = new Map();

let flushTimerId: number | null = null;
let retryTimerId: number | null = null;
let flushPromise: Promise<void> | null = null;
let retryAttempt = 0;
let queueInitialized = false;

function hasWindow() {
  return typeof window !== "undefined";
}

function clearFlushTimer() {
  if (!hasWindow() || flushTimerId === null) {
    return;
  }
  window.clearTimeout(flushTimerId);
  flushTimerId = null;
}

function clearRetryTimer() {
  if (!hasWindow() || retryTimerId === null) {
    return;
  }
  window.clearTimeout(retryTimerId);
  retryTimerId = null;
}

function hasQueuedTelemetry() {
  for (const queue of queuedEventsBySession.values()) {
    if (queue.length > 0) {
      return true;
    }
  }
  return false;
}

function getSessionQueue(sessionId: string) {
  const existing = queuedEventsBySession.get(sessionId);
  if (existing) {
    return existing;
  }
  const created: TelemetryEventRequest[] = [];
  queuedEventsBySession.set(sessionId, created);
  return created;
}

function trimSessionQueue(queue: TelemetryEventRequest[]) {
  if (queue.length <= TELEMETRY_MAX_EVENTS_PER_SESSION) {
    return;
  }
  queue.splice(0, queue.length - TELEMETRY_MAX_EVENTS_PER_SESSION);
}

function upsertSessionEvent(
  queue: TelemetryEventRequest[],
  event: TelemetryEventRequest,
) {
  const nextEvent = {
    ...event,
    client_ts: event.client_ts ?? Date.now(),
  };
  const existingIndex = queue.findIndex(
    (queued) => queued.event_name === nextEvent.event_name,
  );
  if (existingIndex >= 0) {
    queue[existingIndex] = nextEvent;
    return;
  }
  queue.push(nextEvent);
}

function runLowPriority(task: () => void) {
  if (!hasWindow()) {
    task();
    return;
  }
  const idleCallback = window.requestIdleCallback;
  if (typeof idleCallback === "function") {
    idleCallback(task, { timeout: 250 });
    return;
  }
  window.setTimeout(task, 0);
}

function scheduleTelemetryFlush(delayMs = TELEMETRY_FLUSH_INTERVAL_MS) {
  if (!hasWindow() || flushTimerId !== null || retryTimerId !== null) {
    return;
  }
  flushTimerId = window.setTimeout(() => {
    flushTimerId = null;
    void flushTelemetryQueue();
  }, delayMs);
}

function scheduleTelemetryRetry() {
  if (!hasWindow() || retryTimerId !== null) {
    return;
  }
  const nextDelay = Math.min(
    TELEMETRY_RETRY_BASE_MS * 2 ** retryAttempt,
    TELEMETRY_RETRY_MAX_MS,
  );
  retryAttempt += 1;
  retryTimerId = window.setTimeout(() => {
    retryTimerId = null;
    void flushTelemetryQueue();
  }, nextDelay);
}

async function flushSessionQueue(
  sessionId: string,
  keepalive: boolean,
): Promise<boolean> {
  const queue = queuedEventsBySession.get(sessionId);
  if (!queue || queue.length === 0) {
    queuedEventsBySession.delete(sessionId);
    return true;
  }

  while (queue.length > 0) {
    const batch = queue.slice(0, TELEMETRY_BATCH_SIZE);
    try {
      await postTelemetryBatch(
        sessionId,
        batch,
        keepalive ? { keepalive } : undefined,
      );
      queue.splice(0, batch.length);
      retryAttempt = 0;
    } catch {
      return false;
    }
  }

  queuedEventsBySession.delete(sessionId);
  return true;
}

async function flushTelemetryQueue(options: FlushOptions = {}) {
  if (flushPromise) {
    return flushPromise;
  }
  if (!hasQueuedTelemetry()) {
    return Promise.resolve();
  }

  clearFlushTimer();
  clearRetryTimer();

  flushPromise = (async () => {
    const keepalive = options.keepalive ?? false;
    for (const sessionId of Array.from(queuedEventsBySession.keys())) {
      const drained = await flushSessionQueue(sessionId, keepalive);
      if (!drained) {
        scheduleTelemetryRetry();
        break;
      }
    }
  })().finally(() => {
    flushPromise = null;
    if (hasQueuedTelemetry() && retryTimerId === null) {
      scheduleTelemetryFlush();
    }
  });

  return flushPromise;
}

export function initializeTelemetryQueue() {
  if (!hasWindow() || queueInitialized) {
    return;
  }
  queueInitialized = true;

  const flushInBackground = (keepalive = false) => {
    runLowPriority(() => {
      requestTelemetryFlush({ immediate: true, keepalive });
    });
  };

  window.addEventListener("online", () => {
    flushInBackground();
  });
  window.addEventListener("pagehide", () => {
    flushInBackground(true);
  });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      flushInBackground(true);
    }
  });
}

export function queueTelemetryEvent(
  sessionId: string | null | undefined,
  event: TelemetryEventRequest,
  options: FlushOptions = {},
) {
  if (!sessionId) {
    return;
  }

  const queue = getSessionQueue(sessionId);
  upsertSessionEvent(queue, event);
  trimSessionQueue(queue);

  runLowPriority(() => {
    if (options.immediate) {
      void flushTelemetryQueue(options);
      return;
    }
    scheduleTelemetryFlush();
  });
}

export function requestTelemetryFlush(options: FlushOptions = {}) {
  runLowPriority(() => {
    if (options.immediate) {
      void flushTelemetryQueue(options);
      return;
    }
    scheduleTelemetryFlush();
  });
}

export function resetTelemetryQueue(sessionId?: string | null) {
  if (sessionId) {
    queuedEventsBySession.delete(sessionId);
  } else {
    queuedEventsBySession.clear();
  }
  clearFlushTimer();
  clearRetryTimer();
  retryAttempt = 0;
}
