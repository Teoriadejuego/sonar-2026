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
  const { session, submitClaim, pushTelemetry, saveDisplaySnapshot } =
    useSession();
  const { copy, language } = useLanguage();
  const { trackClick } = usePageTelemetry("report");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const shownAtRef = useRef(Date.now());

  if (!session || !session.report_snapshot) {
    return null;
  }

  useEffect(() => {
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
    });
  }, [copy, language, saveDisplaySnapshot, session]);

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
