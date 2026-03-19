import { useState } from "react";
import { ScreenFrame } from "./ScreenFrame";
import { useLanguage } from "../utils/LanguageContext";
import { useSession } from "../utils/SessionContext";
import { translateServerError } from "../utils/uiLexicon";

function isValidEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

export function ExperimentPausedScreen() {
  const { copy } = useLanguage();
  const { submitInterestSignup } = useSession();
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pausedCopy = copy.paused;

  const handleSubmit = async () => {
    if (!isValidEmail(email)) {
      setError(pausedCopy.errorEmail);
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
          : pausedCopy.errorDefault;
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ScreenFrame>
      <div className="flex min-h-full flex-col justify-center gap-8">
        <div className="space-y-4">
          <p className="editorial-eyebrow">
            {pausedCopy.eyebrow}
          </p>
          <h1 className="editorial-title editorial-title--compact">
            {pausedCopy.title}
          </h1>
          <div className="sonar-panel p-5">
            <p className="editorial-body whitespace-pre-line">
              {pausedCopy.body}
            </p>
            <p className="editorial-small mt-3 whitespace-pre-line">
              {pausedCopy.bodySecondary}
            </p>
          </div>
        </div>

        <div className="sonar-panel p-5">
          <label
            htmlFor="future-experiments-email"
            className="sonar-field-label"
          >
            {pausedCopy.emailLabel}
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
            placeholder={pausedCopy.emailPlaceholder}
            disabled={isSubmitting}
            className="sonar-field"
          />
          <p className="editorial-micro mt-3">
            {pausedCopy.legalHint}
          </p>
          {error && (
            <div className="sonar-status sonar-panel-danger mt-4">
              {error}
            </div>
          )}
          {success && (
            <div className="sonar-status sonar-panel-success mt-4">
              {pausedCopy.success}
            </div>
          )}
          <button
            type="button"
            onClick={() => void handleSubmit()}
            disabled={isSubmitting}
            className="sonar-primary-button mt-5"
          >
            {pausedCopy.cta}
          </button>
        </div>
      </div>
    </ScreenFrame>
  );
}
