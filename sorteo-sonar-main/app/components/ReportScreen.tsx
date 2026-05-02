import {
  Component,
  memo,
  type ErrorInfo,
  type ReactNode,
  useCallback,
  useRef,
  useState,
} from "react";
import { ScreenFrame } from "./ScreenFrame";
import { TreatmentBanner } from "./TreatmentBanner";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";
import {
  DeferredRecoveryError,
  useSessionActions,
  useSessionRuntime,
} from "../utils/SessionContext";
import { formatCopy, translateServerError, type UiCopy } from "../utils/uiLexicon";
import type { ReportSnapshot } from "../utils/api";

interface ReportScreenProps {
  onSubmitReport: () => void;
}

type ReportDecisionContentProps = {
  copy: UiCopy;
  snapshot: ReportSnapshot;
  error: string | null;
  recoveryMessage: string | null;
  isSubmitting: boolean;
  isBusy: boolean;
  selectedValue: number | null;
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

const ReportDecisionContent = memo(function ReportDecisionContent({
  copy,
  snapshot,
  error,
  recoveryMessage,
  isSubmitting,
  isBusy,
  selectedValue,
  onReport,
}: ReportDecisionContentProps) {
  return (
    <div className="sonar-screen-stack sonar-screen-stack--report">
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

      {error && !recoveryMessage ? (
        <div className="sonar-status sonar-panel-danger">
          {error}
        </div>
      ) : null}

      {recoveryMessage ? (
        <div className="sonar-status" aria-live="polite">
          {recoveryMessage}
        </div>
      ) : null}

      <div className="sonar-number-grid">
        {[1, 2, 3, 4, 5, 6].map((value) => (
          <button
            key={value}
            onClick={() => void onReport(value)}
            disabled={isSubmitting || isBusy}
            className={`sonar-number-button ${
              selectedValue === value ? "sonar-number-button--selected" : ""
            }`}
          >
            {value}
          </button>
        ))}
      </div>
    </div>
  );
});

const ReportDecisionFallback = memo(function ReportDecisionFallback({
  copy,
  snapshot,
  error,
  recoveryMessage,
  isSubmitting,
  isBusy,
  selectedValue,
  onReport,
}: ReportDecisionContentProps) {
  return (
    <div className="sonar-screen-stack sonar-screen-stack--report">
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

      {error && !recoveryMessage ? (
        <div className="sonar-status sonar-panel-danger">
          {error}
        </div>
      ) : null}

      {recoveryMessage ? (
        <div className="sonar-status" aria-live="polite">
          {recoveryMessage}
        </div>
      ) : null}

      <div className="sonar-number-grid">
        {[1, 2, 3, 4, 5, 6].map((value) => (
          <button
            key={value}
            onClick={() => void onReport(value)}
            disabled={isSubmitting || isBusy}
            className={`sonar-number-button ${
              selectedValue === value ? "sonar-number-button--selected" : ""
            }`}
          >
            {value}
          </button>
        ))}
      </div>
    </div>
  );
});

export const ReportScreen = memo(function ReportScreen({
  onSubmitReport,
}: ReportScreenProps) {
  const { session, networkRecovery, visualTransition } = useSessionRuntime();
  const {
    submitClaim,
    pushTelemetry,
  } = useSessionActions();
  const { copy, language } = useLanguage();
  const { trackClick } = usePageTelemetry("report");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedValue, setSelectedValue] = useState<number | null>(null);
  const shownAtRef = useRef(Date.now());
  const reportSnapshot = session?.report_snapshot ?? null;
  const isPrepareRecovering =
    networkRecovery.phase === "retrying" &&
    networkRecovery.action === "prepare_report";
  const isSubmitRecovering =
    networkRecovery.phase === "retrying" &&
    networkRecovery.action === "submit_claim";
  const isPreparingView =
    visualTransition.phase === "preparing_report" || session?.screen !== "report";
  const recoveryMessage =
    isPrepareRecovering || isSubmitRecovering ? networkRecovery.message : null;

  const handleReport = useCallback(async (value: number) => {
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
    const submittedAt = Date.now();
    setIsSubmitting(true);
    setError(null);
    setSelectedValue(value);
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
      if (err instanceof DeferredRecoveryError) {
        setError(null);
        setIsSubmitting(false);
        return;
      }
      setError(
        err instanceof Error
          ? translateServerError(err.message, copy)
          : copy.report.errorSave,
      );
      setSelectedValue(null);
      setIsSubmitting(false);
    }
  }, [copy, isSubmitting, onSubmitReport, pushTelemetry, submitClaim, trackClick]);

  const handleRenderError = useCallback(
    (renderError: Error, componentStack?: string | null) => {
      pushTelemetry({
        event_type: "error",
        event_name: "report_render_error",
        screen_name: "report",
        payload: {
          message: renderError.message,
          component_stack: componentStack,
        },
      });
    },
    [pushTelemetry],
  );

  if (!session) {
    return null;
  }

  if (!reportSnapshot) {
    return (
      <ScreenFrame>
        <div className="flex min-h-full flex-col items-center justify-center gap-4 text-center">
          <h2 className="editorial-title editorial-title--compact">
            {copy.report.title}
          </h2>
          <div className="sonar-status" aria-live="polite">
            {recoveryMessage ??
              (isPreparingView
                ? copy.common.loadingPrepare
                : copy.game.errors.loadReport)}
          </div>
          {isPreparingView || recoveryMessage ? (
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-slate-950" />
          ) : null}
          <p className="editorial-small">{copy.report.body}</p>
          {error && !recoveryMessage ? (
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
        onRenderError={handleRenderError}
        fallback={
          <ReportDecisionFallback
            copy={copy}
            snapshot={reportSnapshot}
            error={error}
            recoveryMessage={recoveryMessage}
            isSubmitting={isSubmitting}
            isBusy={isPrepareRecovering || isSubmitRecovering}
            selectedValue={selectedValue}
            onReport={handleReport}
          />
        }
      >
        <ReportDecisionContent
          copy={copy}
          snapshot={reportSnapshot}
          error={error}
          recoveryMessage={recoveryMessage}
          isSubmitting={isSubmitting}
          isBusy={isPrepareRecovering || isSubmitRecovering}
          selectedValue={selectedValue}
          onReport={handleReport}
        />
      </ReportDecisionBoundary>
    </ScreenFrame>
  );
});
