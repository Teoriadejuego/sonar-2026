import { useRef, useState } from "react";
import { ScreenFrame } from "./ScreenFrame";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";
import { useSession } from "../utils/SessionContext";

interface ComprehensionScreenProps {
  onPass: () => Promise<void> | void;
}

export function ComprehensionScreen({ onPass }: ComprehensionScreenProps) {
  const { copy } = useLanguage();
  const { pushTelemetry } = useSession();
  const { trackClick } = usePageTelemetry("comprehension");
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPassing, setIsPassing] = useState(false);
  const comprehensionCopy = copy.comprehension;
  const correctOption = comprehensionCopy.options[0];
  const startedAtRef = useRef(Date.now());
  const attemptRef = useRef(0);
  const firstAnswerRef = useRef<string | null>(null);

  const handleSelect = async (option: string) => {
    if (isPassing) {
      return;
    }

    attemptRef.current += 1;
    const now = Date.now();
    const responseMs = now - startedAtRef.current;
    const isCorrect = option === correctOption;
    const attemptNumber = attemptRef.current;
    const completedAt = new Date(now).toISOString();

    if (firstAnswerRef.current === null) {
      firstAnswerRef.current = option;
    }

    setSelected(option);
    trackClick("attention_check_select_option", {
      target: option,
      role: "option",
      ctaKind: "primary",
      payload: {
        option,
        isCorrect,
        attemptNumber,
        responseMs,
      },
    });
    pushTelemetry({
      event_type: "custom",
      event_name: "attention_check_attempt",
      screen_name: "comprehension",
      client_ts: now,
      duration_ms: responseMs,
      payload: {
        selected_option: option,
        attention_check_passed: isCorrect,
        attention_check_attempts: attemptNumber,
        attention_check_first_answer: firstAnswerRef.current,
        attention_check_rt_ms: responseMs,
        attention_check_completed_at: isCorrect ? completedAt : null,
        attention_check_passed_first_try:
          isCorrect && firstAnswerRef.current === correctOption,
      },
    });

    if (!isCorrect) {
      setError(comprehensionCopy.errorWrong);
      return;
    }

    setError(null);
    setIsPassing(true);
    pushTelemetry({
      event_type: "custom",
      event_name: "attention_check_completed",
      screen_name: "comprehension",
      client_ts: now,
      duration_ms: responseMs,
      payload: {
        selected_option: option,
        attention_check_passed: true,
        attention_check_attempts: attemptNumber,
        attention_check_first_answer: firstAnswerRef.current,
        attention_check_rt_ms: responseMs,
        attention_check_completed_at: completedAt,
        attention_check_passed_first_try:
          firstAnswerRef.current === correctOption,
      },
    });
    await onPass();
  };

  return (
    <ScreenFrame>
      <div className="flex min-h-full flex-col gap-8">
        <div className="space-y-4">
          <p className="editorial-eyebrow">
            {comprehensionCopy.eyebrow}
          </p>
          <h2 className="editorial-title editorial-title--compact max-w-[22rem]">
            {comprehensionCopy.title}
          </h2>
        </div>

        <div className="sonar-option-list">
          {comprehensionCopy.options.map((option) => (
            <button
              key={option}
              onClick={() => void handleSelect(option)}
              disabled={isPassing}
              className={`sonar-option-button ${
                selected === option ? "is-selected" : ""
              }`}
            >
              {option}
            </button>
          ))}
        </div>

        {error && (
          <div className="sonar-status sonar-panel-highlight">
            {error}
          </div>
        )}
      </div>
    </ScreenFrame>
  );
}
