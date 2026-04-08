import { useEffect, useMemo } from "react";
import { ScreenFrame } from "./ScreenFrame";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";
import { useSession } from "../utils/SessionContext";

interface FinalScreenProps {
  eyebrow: string;
  footerText: string;
  screenName: "exit_final" | "payout_final";
}

export function FinalScreen({
  eyebrow,
  footerText,
  screenName,
}: FinalScreenProps) {
  const { copy, language } = useLanguage();
  const { saveDisplaySnapshot } = useSession();
  const { trackClick } = usePageTelemetry(screenName);

  const footerMatch = useMemo(
    () => footerText.match(/^(.*?)(cotec\.es)(.*)$/i),
    [footerText],
  );

  useEffect(() => {
    void saveDisplaySnapshot({
      screen_name: screenName,
      language,
      final_message_text: `${footerText} ${copy.common.finalClosingMessage}`,
    });
  }, [copy.common.finalClosingMessage, footerText, language, saveDisplaySnapshot, screenName]);

  return (
    <ScreenFrame>
      <div className="sonar-screen-stack sonar-screen-stack--final justify-center">
        <div className="space-y-3">
          {screenName === "exit_final" ? (
            <h1 className="editorial-title editorial-title--landing exit-kicker-title">
              {eyebrow}
            </h1>
          ) : (
            <p className="editorial-eyebrow">{eyebrow}</p>
          )}
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
                      trackClick("open_cotec_site", {
                        target: "cotec_site",
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
                footerText
              )}
            </p>
          </div>

          <div className="sonar-panel sonar-panel-subtle p-5">
            <p className="editorial-body">{copy.common.finalClosingMessage}</p>
          </div>
        </div>
      </div>
    </ScreenFrame>
  );
}
