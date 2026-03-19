import { useEffect, useState } from "react";
import type { Route } from "./+types/payout";
import { ScreenFrame } from "../components/ScreenFrame";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";
import { useSession } from "../utils/SessionContext";
import { formatCopy, translateServerError, UI_LEXICON } from "../utils/uiLexicon";

export function meta({}: Route.MetaArgs) {
  return [
    { title: `${UI_LEXICON.es.common.appTitle} - ${UI_LEXICON.es.paymentPage.eyebrow}` },
    {
      name: "description",
      content: UI_LEXICON.es.paymentPage.title.replace(/\n/g, " "),
    },
  ];
}

export default function PayoutRoute() {
  const { copy, language, setLanguage } = useLanguage();
  const { lookupPaymentCode, submitPaymentRequest, pushTelemetry } = useSession();
  const { trackClick } = usePageTelemetry("payout");
  const paymentCopy = copy.paymentPage;

  const [code, setCode] = useState("");
  const [phone, setPhone] = useState("");
  const [messageText, setMessageText] = useState("");
  const [lookupState, setLookupState] = useState<{
    status: "idle" | "loading" | "ready" | "invalid" | "used";
    amountEur?: number;
  }>({ status: "idle" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusTone, setStatusTone] = useState<"neutral" | "error" | "success">(
    "neutral",
  );

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const url = new URL(window.location.href);
    const nextCode = url.searchParams.get("code") ?? "";
    const nextLang = url.searchParams.get("lang");
    if (nextCode) {
      setCode(nextCode);
    }
    if (
      nextLang &&
      ["es", "ca", "en", "fr", "pt"].includes(nextLang) &&
      nextLang !== language
    ) {
      setLanguage(nextLang as typeof language);
    }
  }, [language, setLanguage]);

  const translatePaymentError = (message: string) => {
    if (message === "Codigo no elegible para cobro") {
      return paymentCopy.invalidCode;
    }
    if (message === "Codigo de cobro ya utilizado") {
      return paymentCopy.alreadyUsed;
    }
    return translateServerError(message, copy);
  };

  const handleLookup = async () => {
    if (!code.trim()) {
      setStatusTone("error");
      setStatusMessage(paymentCopy.invalidCode);
      return;
    }
    setLookupState({ status: "loading" });
    setStatusMessage(null);
    trackClick("payment_lookup", {
      target: "payment_lookup",
      role: "button",
      ctaKind: "secondary",
    });
    try {
      const response = await lookupPaymentCode(code.trim());
      if (!response.valid) {
        const nextStatus = response.status === "queued" ? "used" : "invalid";
        setLookupState({ status: nextStatus });
        setStatusTone("error");
        setStatusMessage(
          nextStatus === "used"
            ? paymentCopy.alreadyUsed
            : paymentCopy.invalidCode,
        );
        return;
      }
      setLookupState({ status: "ready", amountEur: response.amount_eur });
      setStatusTone("neutral");
      setStatusMessage(
        formatCopy(paymentCopy.lookupHelpTemplate, {
          amount: response.amount_eur,
        }),
      );
    } catch (error) {
      setLookupState({ status: "invalid" });
      setStatusTone("error");
      setStatusMessage(
        error instanceof Error
          ? translatePaymentError(error.message)
          : paymentCopy.errorDefault,
      );
    }
  };

  const handleSubmit = async () => {
    if (lookupState.status !== "ready") {
      await handleLookup();
      return;
    }
    setIsSubmitting(true);
    setStatusMessage(null);
    trackClick("payment_submit", {
      target: "payment_submit",
      role: "button",
      ctaKind: "primary",
    });
    try {
      const response = await submitPaymentRequest(
        code.trim(),
        phone.trim(),
        /\bONG\b/i.test(messageText),
        messageText,
      );
      setStatusTone("success");
      setStatusMessage(paymentCopy.success);
      setLookupState({
        status: "used",
        amountEur: response.amount_eur,
      });
      pushTelemetry({
        event_type: "custom",
        event_name: "payment_request_submitted",
        screen_name: "payout",
        payload: {
          donation_requested: response.donation_requested,
          amount_eur: response.amount_eur,
        },
      });
    } catch (error) {
      setStatusTone("error");
      setStatusMessage(
        error instanceof Error
          ? translatePaymentError(error.message)
          : paymentCopy.errorDefault,
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ScreenFrame>
      <div className="flex min-h-full flex-col gap-6">
        <div className="space-y-3">
          <p className="editorial-eyebrow">
            {paymentCopy.eyebrow}
          </p>
          <h1 className="editorial-title editorial-title--compact whitespace-pre-line">
            {paymentCopy.title}
          </h1>
          {paymentCopy.intro ? (
            <p className="editorial-small max-w-[24rem]">
              {paymentCopy.intro}
            </p>
          ) : null}
        </div>

        <div className="sonar-panel p-5">
          <div className="space-y-4">
            <div>
              <label className="sonar-field-label">
                {paymentCopy.codeLabel}
              </label>
              <input
                value={code}
                onChange={(event) => setCode(event.target.value.trim())}
                className="sonar-field sonar-field--code"
              />
            </div>

            <button
              type="button"
              onClick={() => void handleLookup()}
              className="sonar-secondary-button mx-auto"
            >
              {paymentCopy.lookupLabel}
            </button>

            <div>
              <label className="sonar-field-label">
                {paymentCopy.phoneLabel}
              </label>
              <input
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                placeholder={paymentCopy.phonePlaceholder}
                className="sonar-field"
              />
            </div>

            <div>
              <label className="sonar-field-label">
                {paymentCopy.messageLabel}
              </label>
              <textarea
                value={messageText}
                onChange={(event) => setMessageText(event.target.value)}
                placeholder={paymentCopy.messagePlaceholder}
                className="sonar-textarea"
              />
            </div>
          </div>
        </div>

        <div className="sonar-panel sonar-panel-success p-5">
          <p className="editorial-small text-slate-700">
            {paymentCopy.donationHint}
          </p>
        </div>

        {statusMessage && (
          <div
            className={`sonar-status ${
              statusTone === "success"
                ? "sonar-panel-success"
                : statusTone === "error"
                  ? "sonar-panel-danger"
                  : "sonar-panel"
            }`}
          >
            {statusMessage}
          </div>
        )}

        <button
          type="button"
          onClick={() => void handleSubmit()}
          disabled={isSubmitting}
          className="sonar-primary-button mt-auto"
        >
          {paymentCopy.submitLabel}
        </button>
      </div>
    </ScreenFrame>
  );
}
