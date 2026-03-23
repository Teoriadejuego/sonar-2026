import { useRef, useState } from "react";
import { ConsentModal } from "./ConsentModal";
import { ScreenFrame } from "./ScreenFrame";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";
import { translateServerError } from "../utils/uiLexicon";

type WelcomeScreenProps = {
  onStart: (
    braceletId: string,
    consents: {
      ageConfirmed: boolean;
      participationAccepted: boolean;
      dataAccepted: boolean;
    },
    metrics: {
      landingVisibleMs: number;
      infoPanelsOpened: string[];
      infoPanelDurationsMs: Record<string, number>;
      checkboxOrder: string[];
      checkboxTimestampsMs: Record<string, number>;
      continueBlockedCount: number;
    },
  ) => Promise<string | null>;
  isLoading: boolean;
};

export function WelcomeScreen({ onStart, isLoading }: WelcomeScreenProps) {
  const { copy } = useLanguage();
  const sanitizeBraceletInput = (raw: string) =>
    raw.replace(/[^a-zA-Z0-9]/g, "").toUpperCase().slice(0, 8);
  const [braceletId, setBraceletId] = useState("");
  const [ageConfirmed, setAgeConfirmed] = useState(false);
  const [participationAccepted, setParticipationAccepted] = useState(false);
  const [dataAccepted, setDataAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isInfoOpen, setIsInfoOpen] = useState(false);
  const landingOpenedAtRef = useRef(Date.now());
  const panelOpenedAtRef = useRef<number | null>(null);
  const openedPanelsRef = useRef<Set<string>>(new Set());
  const panelDurationsRef = useRef<Record<string, number>>({});
  const checkboxOrderRef = useRef<string[]>([]);
  const checkboxTimestampsRef = useRef<Record<string, number>>({});
  const blockedContinueCountRef = useRef(0);
  const { trackClick } = usePageTelemetry("landing");

  const landingCopy = copy.landing;
  const allChecked = ageConfirmed && participationAccepted && dataAccepted;
  const infoSections = copy.infoModal.sections;

  const handleSubmit = async () => {
    if (!braceletId.trim()) {
      blockedContinueCountRef.current += 1;
      trackClick("start_blocked_missing_bracelet", {
        target: "start_session",
        role: "button",
        ctaKind: "primary",
      });
      setError(landingCopy.errors.braceletRequired);
      return;
    }
    if (!allChecked) {
      blockedContinueCountRef.current += 1;
      trackClick("start_blocked_missing_consents", {
        target: "start_session",
        role: "button",
        ctaKind: "primary",
        payload: {
          ageConfirmed,
          participationAccepted,
          dataAccepted,
        },
      });
      setError(landingCopy.errors.consentsRequired);
      return;
    }

    const normalized = braceletId.trim().toUpperCase();
    const metrics = {
      landingVisibleMs: Date.now() - landingOpenedAtRef.current,
      infoPanelsOpened: Array.from(openedPanelsRef.current),
      infoPanelDurationsMs: { ...panelDurationsRef.current },
      checkboxOrder: checkboxOrderRef.current,
      checkboxTimestampsMs: { ...checkboxTimestampsRef.current },
      continueBlockedCount: blockedContinueCountRef.current,
    };
    trackClick("start_session", {
      target: "start_session",
      role: "button",
      ctaKind: "primary",
      payload: {
        braceletId: normalized,
        ageConfirmed,
        participationAccepted,
        dataAccepted,
        ...metrics,
      },
    });
    const nextError = await onStart(
      normalized,
      {
        ageConfirmed,
        participationAccepted,
        dataAccepted,
      },
      metrics,
    );
    if (nextError) {
      setError(translateServerError(nextError, copy));
    }
  };

  const openInfoPanel = () => {
    panelOpenedAtRef.current = Date.now();
    openedPanelsRef.current.add("consent_bundle");
    trackClick("open_info_panel", {
      target: "consent_bundle",
      role: "modal_trigger",
      ctaKind: "secondary",
      payload: { panelKey: "consent_bundle" },
    });
    setIsInfoOpen(true);
  };

  const closeInfoPanel = () => {
    const durationMs = panelOpenedAtRef.current
      ? Date.now() - panelOpenedAtRef.current
      : 0;
    panelDurationsRef.current.consent_bundle =
      (panelDurationsRef.current.consent_bundle ?? 0) + durationMs;
    trackClick("close_info_panel", {
      target: "consent_bundle_close",
      role: "modal_close",
      ctaKind: "secondary",
      payload: {
        panelKey: "consent_bundle",
        durationMs,
      },
    });
    panelOpenedAtRef.current = null;
    setIsInfoOpen(false);
  };

  const recordCheckboxTelemetry = (checkboxKey: string, checked: boolean) => {
    if (checked && !checkboxOrderRef.current.includes(checkboxKey)) {
      checkboxOrderRef.current.push(checkboxKey);
      checkboxTimestampsRef.current[checkboxKey] =
        Date.now() - landingOpenedAtRef.current;
    }
    trackClick(`consent_toggle_${checkboxKey}`, {
      target: checkboxKey,
      role: "checkbox",
      payload: { checked },
    });
  };

  return (
    <ScreenFrame>
      <div className="flex min-h-full flex-col justify-between gap-10">
        <div className="space-y-8">
          <div className="space-y-4">
            <p className="editorial-eyebrow">
              {landingCopy.eyebrow}
            </p>
            <h1 className="editorial-title editorial-title--landing max-w-[24rem]">
              {landingCopy.title}
            </h1>
          </div>

          <div className="sonar-panel p-5 sm:p-6">
            <div className="space-y-5">
              <div>
                <label
                  htmlFor="bracelet-id"
                  className="sonar-field-label"
                >
                  {landingCopy.braceletLabel}
                </label>
                <input
                  id="bracelet-id"
                  type="text"
                  value={braceletId}
                  onChange={(event) => {
                    setBraceletId(sanitizeBraceletInput(event.target.value));
                    setError(null);
                  }}
                  placeholder={landingCopy.braceletPlaceholder}
                  disabled={isLoading}
                  maxLength={8}
                  className="sonar-field sonar-field--code"
                />
              </div>

              <div className="flex justify-start">
                <button
                  type="button"
                  onClick={openInfoPanel}
                  className="sonar-text-button"
                >
                  {landingCopy.moreInfoButton}
                </button>
              </div>

              <div className="sonar-checkbox-group">
                <label
                  className={`sonar-checkbox-row ${ageConfirmed ? "is-checked" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={ageConfirmed}
                    onChange={(event) => {
                      setAgeConfirmed(event.target.checked);
                      setError(null);
                      recordCheckboxTelemetry("age", event.target.checked);
                    }}
                    className="sonar-checkbox"
                  />
                  <span className="sonar-checkbox-label">
                    {landingCopy.ageCheckbox}
                  </span>
                </label>

                <label
                  className={`sonar-checkbox-row ${participationAccepted ? "is-checked" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={participationAccepted}
                    onChange={(event) => {
                      setParticipationAccepted(event.target.checked);
                      setError(null);
                      recordCheckboxTelemetry(
                        "participation",
                        event.target.checked,
                      );
                    }}
                    className="sonar-checkbox"
                  />
                  <span className="sonar-checkbox-label">
                    {landingCopy.participationCheckbox}
                  </span>
                </label>

                <label
                  className={`sonar-checkbox-row ${dataAccepted ? "is-checked" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={dataAccepted}
                    onChange={(event) => {
                      setDataAccepted(event.target.checked);
                      setError(null);
                      recordCheckboxTelemetry("data", event.target.checked);
                    }}
                    className="sonar-checkbox"
                  />
                  <span className="sonar-checkbox-label">
                    {landingCopy.dataCheckbox}
                  </span>
                </label>
              </div>

              {error && (
                <div className="sonar-status sonar-panel-danger">
                  {error}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <button
            onClick={handleSubmit}
            disabled={isLoading}
            className="sonar-primary-button"
          >
            {isLoading ? landingCopy.errors.loading : landingCopy.cta}
          </button>
          {landingCopy.footer ? (
            <p className="editorial-micro text-center">
              {landingCopy.footer}
            </p>
          ) : null}
        </div>
      </div>

      <ConsentModal
        isOpen={isInfoOpen}
        title={copy.infoModal.title}
        sections={infoSections}
        closeLabel={copy.common.close}
        onClose={closeInfoPanel}
      />
    </ScreenFrame>
  );
}
