import { useEffect } from "react";
import { Link } from "react-router";
import { BonusDrawPanel } from "./BonusDrawPanel";
import { ScreenFrame } from "./ScreenFrame";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";
import { useSession } from "../utils/SessionContext";
import { formatCopy } from "../utils/uiLexicon";

function sanitizeWhatsappPhone(rawPhone: string) {
  const digitsOnly = rawPhone.replace(/\D/g, "");
  if (digitsOnly.startsWith("00")) {
    return digitsOnly.slice(2);
  }
  return digitsOnly;
}

export function ExitScreen() {
  const { session, publicConfig, saveDisplaySnapshot, pushTelemetry } = useSession();
  const { copy, language } = useLanguage();
  const { trackClick } = usePageTelemetry("exit");

  if (!session) {
    return null;
  }

  const inviteLink =
    typeof window === "undefined"
      ? ""
      : `${window.location.origin}${window.location.pathname}?ref=${encodeURIComponent(session.referral_code)}&src=whatsapp`;
  const loserCopy = copy.loser;
  const whatsappText = encodeURIComponent(
    formatCopy(loserCopy.shareMessageTemplate, { link: inviteLink }),
  );
  const whatsappLink = `https://wa.me/?text=${whatsappText}`;

  const winnerCopy = copy.winner;
  const bonusCopy = copy.bonusDraw;
  const winnerCode = session.payment.reference_code ?? "-";
  const winnerAmount = session.payment.amount_eur.toFixed(0);
  const payoutPageLink = `/payout?code=${encodeURIComponent(winnerCode)}&lang=${encodeURIComponent(language)}`;
  const cotecMatch = loserCopy.bodyFooter.match(/^(.*?)(cotec\.es)(.*)$/i);

  useEffect(() => {
    const finalMessageText = session.payment.eligible
      ? `${winnerCopy.eyebrow}. ${winnerCopy.title}. ${formatCopy(
          winnerCopy.codeLabelTemplate,
          { code: winnerCode },
        )}`
      : `${loserCopy.body} ${loserCopy.bodySecondary} ${loserCopy.bodyFooter}`;
    void saveDisplaySnapshot({
      screen_name: "exit",
      language,
      final_message_text: finalMessageText,
      final_amount_eur: session.payment.eligible
        ? Math.round(session.payment.amount_eur)
        : 0,
      payout_reference_shown: session.payment.eligible ? winnerCode : undefined,
      payout_phone_shown: session.payment.eligible
        ? sanitizeWhatsappPhone(publicConfig.support.winner_whatsapp_phone)
        : undefined,
    });
  }, [
    language,
    loserCopy.body,
    loserCopy.bodyFooter,
    loserCopy.bodySecondary,
    publicConfig.support.winner_whatsapp_phone,
    saveDisplaySnapshot,
    session.payment.amount_eur,
    session.payment.eligible,
    winnerCode,
    winnerCopy.codeLabelTemplate,
    winnerCopy.eyebrow,
    winnerCopy.title,
  ]);

  return (
    <ScreenFrame>
      <div className="flex min-h-full flex-col justify-between gap-8">
        <div className="space-y-5">
          {session.payment.eligible ? (
            <>
              <div className="space-y-3">
                <p className="editorial-eyebrow">{winnerCopy.eyebrow}</p>
                <h2 className="editorial-title editorial-title--compact">
                  {winnerCopy.title}
                </h2>
              </div>

              <div className="sonar-panel sonar-panel-success p-5">
                <p className="editorial-eyebrow text-slate-700">
                  {winnerCopy.amountLabel}
                </p>
                <p className="sonar-kpi-value mt-3">
                  {winnerAmount} {"\u20ac"}
                </p>
              </div>

              <div className="sonar-panel p-5">
                <p className="editorial-small mb-3">
                  {formatCopy(winnerCopy.codeLabelTemplate, {
                    code: winnerCode,
                  })}
                </p>
                <div className="sonar-ticket-code">{winnerCode}</div>
              </div>

              <Link
                to={payoutPageLink}
                onClick={() =>
                  trackClick("winner_payout_page", {
                    target: "winner_payout_page",
                    role: "link",
                    ctaKind: "primary",
                  })
                }
                className="sonar-primary-button"
              >
                {winnerCopy.cta}
              </Link>
            </>
          ) : (
            <>
              <div className="space-y-3">
                <p className="editorial-eyebrow">{loserCopy.eyebrow}</p>
                <h2 className="editorial-title editorial-title--compact">
                  {loserCopy.title}
                </h2>
              </div>

              <div className="sonar-panel p-5">
                <p className="editorial-body">{loserCopy.body}</p>
              </div>

              <div className="sonar-panel sonar-panel-highlight p-5">
                <div className="space-y-4">
                  <p className="editorial-body">{loserCopy.bodySecondary}</p>
                  <BonusDrawPanel
                    copy={bonusCopy}
                    storageKey={`sonar_bonus_prediction:${session.session_id}:${session.claim?.submitted_at ?? session.valid_completed_at ?? "current"}`}
                    onSelect={(value) => {
                      trackClick("bonus_prediction_exit", {
                        target: `bonus_prediction_${value}`,
                        role: "button",
                        ctaKind: "secondary",
                        value,
                      });
                      pushTelemetry({
                        event_type: "custom",
                        event_name: "bonus_prediction_selected",
                        screen_name: "exit",
                        value,
                        payload: {
                          session_id: session.session_id,
                          referral_code: session.referral_code,
                        },
                      });
                    }}
                  >
                    <a
                      href={whatsappLink}
                      target="_blank"
                      rel="noreferrer"
                      onClick={() =>
                        trackClick("share_whatsapp", {
                          target: "share_whatsapp",
                          role: "link",
                          ctaKind: "secondary",
                          payload: {
                            referralCode: session.referral_code,
                            referralSource: "whatsapp",
                            bonusPredictionStored: true,
                          },
                        })
                      }
                      className="sonar-share-button w-full"
                    >
                      {loserCopy.shareLabel}
                    </a>
                  </BonusDrawPanel>
                </div>
              </div>

              <div className="sonar-panel p-5">
                <p className="editorial-small">
                  {cotecMatch ? (
                    <>
                      {cotecMatch[1]}
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
                        {cotecMatch[2]}
                      </a>
                      {cotecMatch[3]}
                    </>
                  ) : (
                    loserCopy.bodyFooter
                  )}
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </ScreenFrame>
  );
}
