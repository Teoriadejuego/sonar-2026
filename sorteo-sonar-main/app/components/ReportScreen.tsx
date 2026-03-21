import { useEffect, useRef, useState } from "react";
import { ScreenFrame } from "./ScreenFrame";
import { TreatmentBanner } from "./TreatmentBanner";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";
import { useSession } from "../utils/SessionContext";
import { formatCopy, translateServerError } from "../utils/uiLexicon";

interface ReportScreenProps {
  onSubmitReport: () => void;
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
    const socialMessage = formatCopy(copy.treatment.socialMessageTemplate, {
      count: snapshot.count_target ?? "-",
      denominator: snapshot.denominator ?? "-",
      target: snapshot.target_value ?? "-",
    });
    const treatmentMessageText = snapshot.is_control
      ? `${copy.treatment.controlTitle}. ${copy.treatment.controlBody}`
      : socialMessage;
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

  return (
    <ScreenFrame>
      <div className="flex min-h-full flex-col gap-6">
        <div className="space-y-3">
          <h2 className="editorial-title editorial-title--compact">
            {copy.report.title}
          </h2>
        </div>

        <TreatmentBanner snapshot={session.report_snapshot} />

        <div className="sonar-panel p-5">
          <p className="editorial-body">
            {copy.report.body}
          </p>
        </div>

        {error && (
          <div className="sonar-status sonar-panel-danger">
            {error}
          </div>
        )}

        <div className="sonar-number-grid">
          {[1, 2, 3, 4, 5, 6].map((value) => (
            <button
              key={value}
              onClick={() => void handleReport(value)}
              disabled={isSubmitting}
              className="sonar-number-button"
            >
              {value}
            </button>
          ))}
        </div>
      </div>
    </ScreenFrame>
  );
}
