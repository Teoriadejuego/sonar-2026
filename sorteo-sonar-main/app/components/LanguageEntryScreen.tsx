import { LanguageSwitcher } from "./LanguageSwitcher";
import { ScreenFrame } from "./ScreenFrame";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";

export function LanguageEntryScreen({
  onContinue,
}: {
  onContinue: () => void;
}) {
  const { copy } = useLanguage();
  const { trackClick } = usePageTelemetry("language");

  return (
    <ScreenFrame hideLanguageSwitcher contentClassName="min-h-full">
      <div className="flex min-h-full flex-col items-center justify-center">
        <div className="w-full max-w-3xl space-y-10 text-center">
          {copy.languageEntry.title ? (
            <div className="space-y-4">
              <h1 className="editorial-title whitespace-pre-line">
                {copy.languageEntry.title}
              </h1>
            </div>
          ) : null}

          <LanguageSwitcher
            variant="welcome"
            onLanguageSelected={(language) => {
              trackClick("select_language_gate", {
                target: `language_${language}`,
                role: "button",
                ctaKind: "primary",
                payload: { language },
              });
              onContinue();
            }}
          />

          {copy.languageEntry.subtitle ? (
            <p className="editorial-micro mx-auto max-w-[18rem] text-slate-500">
              {copy.languageEntry.subtitle}
            </p>
          ) : null}
        </div>
      </div>
    </ScreenFrame>
  );
}
