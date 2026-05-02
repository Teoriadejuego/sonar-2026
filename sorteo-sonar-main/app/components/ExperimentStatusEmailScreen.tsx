import { memo, useState } from "react";
import { ScreenFrame } from "./ScreenFrame";
import { useLanguage } from "../utils/LanguageContext";
import { useSessionActions } from "../utils/SessionContext";
import { translateServerError, type UiCopy } from "../utils/uiLexicon";

function isValidEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

type ExperimentStatusEmailScreenProps = {
  copyBlock: UiCopy["paused"] | UiCopy["closed"];
};

export const ExperimentStatusEmailScreen = memo(
  function ExperimentStatusEmailScreen({
    copyBlock,
  }: ExperimentStatusEmailScreenProps) {
    const { copy } = useLanguage();
    const { submitInterestSignup } = useSessionActions();
    const [email, setEmail] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async () => {
      if (!isValidEmail(email)) {
        setError(copyBlock.errorEmail);
        return;
      }
      setIsSubmitting(true);
      setError(null);
      try {
        await submitInterestSignup(email.trim());
        setSuccess(true);
        setEmail("");
      } catch (submitError) {
        const message =
          submitError instanceof Error
            ? translateServerError(submitError.message, copy)
            : copyBlock.errorDefault;
        setError(message);
      } finally {
        setIsSubmitting(false);
      }
    };

    return (
      <ScreenFrame>
        <div className="flex min-h-full flex-col justify-center gap-8">
          <div className="space-y-4">
            <p className="editorial-eyebrow">{copyBlock.eyebrow}</p>
            <h1 className="editorial-title editorial-title--compact">
              {copyBlock.title}
            </h1>
            <div className="sonar-panel p-5">
              <p className="editorial-body whitespace-pre-line">
                {copyBlock.body}
              </p>
              <p className="editorial-small mt-3 whitespace-pre-line">
                {copyBlock.bodySecondary}
              </p>
            </div>
          </div>

          <div className="sonar-panel p-5">
            <label htmlFor="future-experiments-email" className="sonar-field-label">
              {copyBlock.emailLabel}
            </label>
            <input
              id="future-experiments-email"
              type="email"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setError(null);
                setSuccess(false);
              }}
              placeholder={copyBlock.emailPlaceholder}
              disabled={isSubmitting}
              className="sonar-field"
            />
            <p className="editorial-micro mt-3">{copyBlock.legalHint}</p>
            {error ? (
              <div className="sonar-status sonar-panel-danger mt-4">
                {error}
              </div>
            ) : null}
            {success ? (
              <div className="sonar-status sonar-panel-success mt-4">
                {copyBlock.success}
              </div>
            ) : null}
            <button
              type="button"
              onClick={() => void handleSubmit()}
              disabled={isSubmitting}
              className="sonar-primary-button mt-5"
            >
              {copyBlock.cta}
            </button>
          </div>
        </div>
      </ScreenFrame>
    );
  },
);
