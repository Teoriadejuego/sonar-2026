import { useEffect, useMemo, useRef, useState } from "react";
import type { Route } from "./+types/payout";
import { BonusDrawPanel } from "../components/BonusDrawPanel";
import { ConsentModal } from "../components/ConsentModal";
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

function normalizePhoneInput(raw: string) {
  const hasPlus = raw.trim().startsWith("+");
  const digits = raw.replace(/\D/g, "").slice(0, 15);
  return hasPlus ? `+${digits}` : digits;
}

function hasValidPhone(raw: string) {
  const digits = raw.replace(/\D/g, "");
  return digits.length >= 9 && digits.length <= 15;
}

export default function PayoutRoute() {
  const { copy, language, setLanguage } = useLanguage();
  const { lookupPaymentCode, submitPaymentRequest, pushTelemetry } = useSession();
  const { trackClick } = usePageTelemetry("payout");
  const paymentCopy = copy.paymentPage;
  const bonusCopy = copy.bonusDraw;

  const [code, setCode] = useState("");
  const [phone, setPhone] = useState("");
  const [lookupState, setLookupState] = useState<{
    status: "idle" | "loading" | "ready" | "invalid" | "used";
    amountEur?: number;
  }>({ status: "idle" });
  const [hasPaymentConsent, setHasPaymentConsent] = useState(false);
  const [isPrivacyModalOpen, setIsPrivacyModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusTone, setStatusTone] = useState<"neutral" | "error" | "success">(
    "neutral",
  );
  const [wasDonationRequest, setWasDonationRequest] = useState(false);
  const [successBonusStorageKey, setSuccessBonusStorageKey] = useState<string | null>(
    null,
  );
  const autoLookupPendingRef = useRef(false);

  const inviteLink =
    typeof window === "undefined"
      ? ""
      : `${window.location.origin}/`;
  const whatsappText = encodeURIComponent(
    formatCopy(paymentCopy.successShareMessageTemplate, {
      link: inviteLink,
    }),
  );
  const whatsappLink = `https://wa.me/?text=${whatsappText}`;

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const url = new URL(window.location.href);
    const nextCode = url.searchParams.get("code") ?? "";
    const nextLang = url.searchParams.get("lang");
    if (nextCode) {
      setCode(nextCode.trim().toUpperCase());
      autoLookupPendingRef.current = true;
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

  const handleLookup = async (incomingCode?: string, source: "auto" | "manual" | "submit" = "manual") => {
    const lookupCode = (incomingCode ?? code).trim().toUpperCase();
    if (!lookupCode) {
      setLookupState({ status: "invalid" });
      setStatusTone("error");
      setStatusMessage(paymentCopy.invalidCode);
      return null;
    }
    setLookupState({ status: "loading" });
    setStatusMessage(null);

    if (source === "manual") {
      trackClick("payment_lookup", {
        target: "payment_lookup",
        role: "button",
        ctaKind: "secondary",
      });
    }

    try {
      const response = await lookupPaymentCode(lookupCode);
      if (!response.valid) {
        const nextStatus = response.status === "queued" ? "used" : "invalid";
        setLookupState({ status: nextStatus });
        setStatusTone("error");
        setStatusMessage(
          nextStatus === "used"
            ? paymentCopy.alreadyUsed
            : paymentCopy.invalidCode,
        );
        return null;
      }
      setLookupState({ status: "ready", amountEur: response.amount_eur });
      setStatusTone("neutral");
      setStatusMessage(
        formatCopy(paymentCopy.lookupHelpTemplate, {
          amount: response.amount_eur,
        }),
      );
      return response;
    } catch (error) {
      setLookupState({ status: "invalid" });
      setStatusTone("error");
      setStatusMessage(
        error instanceof Error
          ? translatePaymentError(error.message)
          : paymentCopy.errorDefault,
      );
      return null;
    }
  };

  useEffect(() => {
    if (!autoLookupPendingRef.current || !code.trim()) {
      return;
    }
    autoLookupPendingRef.current = false;
    void handleLookup(code, "auto");
  }, [code]);

  const handleSubmit = async (donationRequested: boolean) => {
    const normalizedCode = code.trim().toUpperCase();
    const normalizedPhone = phone.trim();

    if (!normalizedCode) {
      setStatusTone("error");
      setStatusMessage(paymentCopy.invalidCode);
      return;
    }

    if (!donationRequested && !hasValidPhone(normalizedPhone)) {
      setStatusTone("error");
      setStatusMessage(paymentCopy.phoneRequired);
      return;
    }

    if (!donationRequested && !hasPaymentConsent) {
      setStatusTone("error");
      setStatusMessage(paymentCopy.consentRequired);
      return;
    }

    if (lookupState.status !== "ready") {
      const readyResponse = await handleLookup(normalizedCode, "submit");
      if (!readyResponse) {
        return;
      }
    }

    setIsSubmitting(true);
    setStatusMessage(null);
    setStatusTone("neutral");
    trackClick(donationRequested ? "payment_donate" : "payment_submit", {
      target: donationRequested ? "payment_donate" : "payment_submit",
      role: "button",
      ctaKind: donationRequested ? "secondary" : "primary",
    });

    try {
      const response = await submitPaymentRequest(
        normalizedCode,
        donationRequested ? "" : normalizedPhone,
        donationRequested,
      );
      setWasDonationRequest(donationRequested);
      setSuccessBonusStorageKey(
        `sonar_bonus_prediction:payout:${normalizedCode}:${Date.now()}`,
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
          payment_code: normalizedCode,
        },
      });
      setIsSubmitted(true);
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

  const footerMatch = useMemo(
    () => paymentCopy.successFooter.match(/^(.*?)(cotec\.es)(.*)$/i),
    [paymentCopy.successFooter],
  );

  if (isSubmitted) {
    return (
      <ScreenFrame>
        <div className="flex min-h-full flex-col justify-between gap-8">
          <div className="space-y-5">
            <div className="space-y-3">
              <p className="editorial-eyebrow">{paymentCopy.successEyebrow}</p>
              <h1 className="editorial-title editorial-title--compact">
                {paymentCopy.successTitle}
              </h1>
            </div>

            <div className="sonar-panel p-5">
              <p className="editorial-body">
                {wasDonationRequest
                  ? paymentCopy.successDonationBody
                  : paymentCopy.successBody}
              </p>
            </div>

            <div className="sonar-panel sonar-panel-highlight p-5">
              <div className="space-y-4">
                <p className="editorial-body">{paymentCopy.successSecondary}</p>
                <BonusDrawPanel
                  copy={bonusCopy}
                  storageKey={
                    successBonusStorageKey ??
                    `sonar_bonus_prediction:payout:${code.trim().toUpperCase() || "unknown"}:success`
                  }
                  onSelect={(value) => {
                    trackClick("bonus_prediction_payout_success", {
                      target: `bonus_prediction_${value}`,
                      role: "button",
                      ctaKind: "secondary",
                      value,
                    });
                    pushTelemetry({
                      event_type: "custom",
                      event_name: "bonus_prediction_selected",
                      screen_name: "payout_success",
                      value,
                      payload: {
                        payment_code: code.trim().toUpperCase() || null,
                        donation_requested: wasDonationRequest,
                      },
                    });
                  }}
                />
                <p className="editorial-small text-slate-700">
                  {bonusCopy.inviteTicket}
                </p>
                <a
                  href={whatsappLink}
                  target="_blank"
                  rel="noreferrer"
                  onClick={() =>
                    trackClick("payment_success_share_whatsapp", {
                      target: "payment_success_share_whatsapp",
                      role: "link",
                      ctaKind: "secondary",
                    })
                  }
                  className="sonar-share-button"
                >
                  {paymentCopy.successShareLabel}
                </a>
              </div>
            </div>

            <div className="sonar-panel p-5">
              <p className="editorial-small">
                {footerMatch ? (
                  <>
                    {footerMatch[1]}
                    <a
                      href="https://cotec.es"
                      target="_blank"
                      rel="noreferrer"
                      onClick={() =>
                        trackClick("payment_success_open_cotec", {
                          target: "payment_success_cotec",
                          role: "link",
                          ctaKind: "secondary",
                        })
                      }
                      className="font-semibold text-slate-950 underline decoration-slate-400 underline-offset-3 transition hover:decoration-slate-950"
                    >
                      {footerMatch[2]}
                    </a>
                    {footerMatch[3]}
                  </>
                ) : (
                  paymentCopy.successFooter
                )}
              </p>
            </div>
          </div>
        </div>
      </ScreenFrame>
    );
  }

  return (
    <ScreenFrame>
      <>
        <div className="flex min-h-full flex-col gap-6">
          <div className="space-y-3">
            <p className="editorial-eyebrow">{paymentCopy.eyebrow}</p>
            <h1 className="editorial-title editorial-title--compact whitespace-pre-line">
              {paymentCopy.title}
            </h1>
            {paymentCopy.intro ? (
              <p className="editorial-small max-w-[26rem]">{paymentCopy.intro}</p>
            ) : null}
          </div>

          <div className="sonar-panel p-5">
            <div className="space-y-4">
              <div>
                <label className="sonar-field-label">{paymentCopy.codeLabel}</label>
                <input
                  value={code}
                  readOnly
                  className="sonar-field sonar-field--code"
                />
              </div>

              <div>
                <label className="sonar-field-label">{paymentCopy.phoneLabel}</label>
                <input
                  value={phone}
                  onChange={(event) =>
                    setPhone(normalizePhoneInput(event.target.value))
                  }
                  placeholder={paymentCopy.phonePlaceholder}
                  inputMode="tel"
                  autoComplete="tel"
                  className="sonar-field"
                />
              </div>

              <div
                className={`sonar-checkbox-card ${
                  hasPaymentConsent ? "is-checked" : ""
                }`}
              >
                <input
                  id="payment-privacy-consent"
                  type="checkbox"
                  checked={hasPaymentConsent}
                  onChange={(event) =>
                    setHasPaymentConsent(event.target.checked)
                  }
                  className="sonar-checkbox"
                />
                <div className="min-w-0 flex-1 space-y-3">
                  <label
                    htmlFor="payment-privacy-consent"
                    className="sonar-checkbox-label block"
                  >
                    {paymentCopy.consentLabel}
                  </label>
                  <button
                    type="button"
                    onClick={() => setIsPrivacyModalOpen(true)}
                    className="sonar-text-button mx-auto"
                  >
                    {paymentCopy.consentInfoLabel}
                  </button>
                </div>
              </div>
            </div>
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

          <div className="mt-auto space-y-3">
            <button
              type="button"
              onClick={() => void handleSubmit(false)}
              disabled={isSubmitting}
              className="sonar-primary-button"
            >
              {paymentCopy.submitLabel}
            </button>

            <div className="space-y-2">
              <p className="editorial-small text-center">{paymentCopy.donationHint}</p>
              <button
                type="button"
                onClick={() => void handleSubmit(true)}
                disabled={isSubmitting}
                className="sonar-secondary-button w-full"
              >
                {paymentCopy.donateLabel}
              </button>
            </div>
          </div>
        </div>

        <ConsentModal
          isOpen={isPrivacyModalOpen}
          title={paymentCopy.privacyModalTitle}
          sections={paymentCopy.privacySections}
          closeLabel={copy.common.close}
          onClose={() => setIsPrivacyModalOpen(false)}
        />
      </>
    </ScreenFrame>
  );
}
