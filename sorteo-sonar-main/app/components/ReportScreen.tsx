import { Component, type ErrorInfo, type ReactNode, useEffect, useRef, useState } from "react";
import { ScreenFrame } from "./ScreenFrame";
import { TreatmentBanner } from "./TreatmentBanner";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";
import { useSession } from "../utils/SessionContext";
import { formatCopy, translateServerError, type UiCopy } from "../utils/uiLexicon";
import type { ReportSnapshot } from "../utils/api";

interface ReportScreenProps {
  onSubmitReport: () => void;
}

type ReportDecisionContentProps = {
  copy: UiCopy;
  snapshot: ReportSnapshot;
  error: string | null;
  isSubmitting: boolean;
  onReport: (value: number) => Promise<void>;
};

type ReportDecisionBoundaryProps = {
  fallback: ReactNode;
  onRenderError: (error: Error, componentStack?: string | null) => void;
  children: ReactNode;
};

type ReportDecisionBoundaryState = {
  hasError: boolean;
};

class ReportDecisionBoundary extends Component<
  ReportDecisionBoundaryProps,
  ReportDecisionBoundaryState
> {
  override state: ReportDecisionBoundaryState = {
    hasError: false,
  };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    this.props.onRenderError(error, info.componentStack);
  }

  override render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

function buildTreatmentMessage(snapshot: ReportSnapshot, copy: UiCopy) {
  if (snapshot.is_control) {
    return `${copy.treatment.controlTitle}. ${copy.treatment.controlBody}`;
  }
  return formatCopy(copy.treatment.socialMessageTemplate, {
    count: snapshot.count_target ?? "-",
    denominator: snapshot.denominator ?? "-",
    target: snapshot.target_value ?? "-",
  });
}

function ReportDecisionContent({
  copy,
  snapshot,
  error,
  isSubmitting,
  onReport,
}: ReportDecisionContentProps) {
  return (
    <div className="flex min-h-full flex-col gap-6">
      <div className="space-y-3">
        <h2 className="editorial-title editorial-title--compact">
          {copy.report.title}
        </h2>
      </div>

      <TreatmentBanner snapshot={snapshot} />

      <div className="sonar-panel p-5">
        <p className="editorial-body">
          {copy.report.body}
        </p>
      </div>

      {error ? (
        <div className="sonar-status sonar-panel-danger">
          {error}
        </div>
      ) : null}

      <div className="sonar-number-grid">
        {[1, 2, 3, 4, 5, 6].map((value) => (
          <button
            key={value}
            onClick={() => void onReport(value)}
            disabled={isSubmitting}
            className="sonar-number-button"
          >
            {value}
          </button>
        ))}
      </div>
    </div>
  );
}

function ReportDecisionFallback({
  copy,
  snapshot,
  error,
  isSubmitting,
  onReport,
}: ReportDecisionContentProps) {
  return (
    <div className="flex min-h-full flex-col gap-6">
      <div className="space-y-3">
        <h2 className="editorial-title editorial-title--compact">
          {copy.report.title}
        </h2>
      </div>

      <div className="sonar-panel sonar-panel-highlight w-full p-5 text-left">
        <p className="editorial-body font-semibold text-slate-950">
          {buildTreatmentMessage(snapshot, copy)}
        </p>
      </div>

      <div className="sonar-panel p-5">
        <p className="editorial-body">
          {copy.report.body}
        </p>
      </div>

      {error ? (
        <div className="sonar-status sonar-panel-danger">
          {error}
        </div>
      ) : null}

      <div className="sonar-number-grid">
        {[1, 2, 3, 4, 5, 6].map((value) => (
          <button
            key={value}
            onClick={() => void onReport(value)}
            disabled={isSubmitting}
            className="sonar-number-button"
          >
            {value}
          </button>
        ))}
      </div>
    </div>
  );
}

export function ReportScreen({ onSubmitReport }: ReportScreenProps) {
  const {
    session,
    submitClaim,
    pushTelemetry,
    saveDisplaySnapshot,
    prepareForReport,
  } =
    useSession();
  const { copy, language } = useLanguage();
  const { trackClick } = usePageTelemetry("report");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRecovering, setIsRecovering] = useState(false);
  const shownAtRef = useRef(Date.now());

  useEffect(() => {
    if (!session || session.report_snapshot || isRecovering) {
      return;
    }

    let cancelled = false;
    setIsRecovering(true);
    setError(null);

    void prepareForReport()
      .catch((err) => {
        if (cancelled) {
          return;
        }
        setError(
          err instanceof Error
            ? translateServerError(err.message, copy)
            : copy.game.errors.loadReport,
        );
      })
      .finally(() => {
        if (!cancelled) {
          setIsRecovering(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [copy, isRecovering, prepareForReport, session]);

  useEffect(() => {
    if (!session) {
      return;
    }
    const snapshot = session.report_snapshot;
    if (!snapshot) {
      return;
    }
    const treatmentMessageText = buildTreatmentMessage(snapshot, copy);
    void saveDisplaySnapshot({
      screen_name: "report",
      language,
      treatment_message_text: treatmentMessageText,
      control_message_text: snapshot.is_control
        ? `${copy.treatment.controlTitle}. ${copy.treatment.controlBody}`
        : undefined,
      rerolls_visible: session.throws.slice(1).map((item) => item.result_value),
    }).catch(() => {
      // The report UI should stay usable even if snapshot persistence fails.
    });
  }, [copy, language, saveDisplaySnapshot, session]);

  if (!session) {
    return null;
  }

  const handleReport = async (value: number) => {
    if (isSubmitting) {
      trackClick("report_click_ignored_while_submitting", {
        target: `report_${value}`,
        role: "button",
        ctaKind: "primary",
        value,
      });
      return;
    }
    const reactionMs = Date.now() - shownAtRef.current;
    setIsSubmitting(true);
    setError(null);
    trackClick(`report_${value}`, {
      target: `report_value_${value}`,
      role: "button",
      ctaKind: "primary",
      value,
      payload: { reactionMs },
    });

    try {
      await submitClaim(value, reactionMs);
      pushTelemetry({
        event_type: "custom",
        event_name: "claim_submitted",
        screen_name: "report",
        client_ts: Date.now(),
        duration_ms: reactionMs,
        value,
      });
      onSubmitReport();
    } catch (err) {
      setError(
        err instanceof Error
          ? translateServerError(err.message, copy)
          : copy.report.errorSave,
      );
      setIsSubmitting(false);
    }
  };

  if (!session.report_snapshot) {
    return (
      <ScreenFrame>
        <div className="flex min-h-full flex-col items-center justify-center gap-4 text-center">
          <div className="h-14 w-14 animate-spin rounded-full border-4 border-slate-200 border-t-slate-950" />
          <p className="editorial-small">
            {isRecovering ? copy.common.loadingPrepare : copy.game.errors.loadReport}
          </p>
          {error ? (
            <div className="sonar-status sonar-panel-danger w-full max-w-[28rem]">
              {error}
            </div>
          ) : null}
        </div>
      </ScreenFrame>
    );
  }

  return (
    <ScreenFrame>
      <ReportDecisionBoundary
        onRenderError={(renderError, componentStack) => {
          pushTelemetry({
            event_type: "error",
            event_name: "report_render_error",
            screen_name: "report",
            payload: {
              message: renderError.message,
              component_stack: componentStack,
            },
          });
        }}
        fallback={
          <ReportDecisionFallback
            copy={copy}
            snapshot={session.report_snapshot}
            error={error}
            isSubmitting={isSubmitting}
            onReport={handleReport}
          />
        }
      >
        <ReportDecisionContent
          copy={copy}
          snapshot={session.report_snapshot}
          error={error}
          isSubmitting={isSubmitting}
          onReport={handleReport}
        />
      </ReportDecisionBoundary>
    </ScreenFrame>
  );
}
