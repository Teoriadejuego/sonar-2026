import { memo, useEffect } from "react";
import { Link } from "react-router";
import { BonusDrawPanel } from "./BonusDrawPanel";
import { ScreenFrame } from "./ScreenFrame";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";
import {
  useSessionActions,
  useSessionRuntime,
} from "../utils/SessionContext";
import { formatCopy } from "../utils/uiLexicon";

interface ExitScreenProps {
  onContinueToFinal: () => void;
}

function sanitizeWhatsappPhone(rawPhone: string) {
  const digitsOnly = rawPhone.replace(/\D/g, "");
  if (digitsOnly.startsWith("00")) {
    return digitsOnly.slice(2);
  }
  return digitsOnly;
}

export const ExitScreen = memo(function ExitScreen({
  onContinueToFinal,
}: ExitScreenProps) {
  const { session } = useSessionRuntime();
  const {
    createReferralInviteLink,
    pushTelemetry,
    submitClaimFollowup,
  } = useSessionActions();
  const { copy, language } = useLanguage();
  const { trackClick } = usePageTelemetry("exit");
  const winnerCopy = copy.winner;
  const bonusCopy = copy.bonusDraw;
  const loserCopy = copy.loser;
  const winnerCode = session?.payment.reference_code ?? "-";
  const winnerAmount = session?.payment.amount_eur.toFixed(0) ?? "0";
  const payoutPageLink = `/payout?code=${encodeURIComponent(winnerCode)}&lang=${encodeURIComponent(language)}`;

  if (!session) {
    return null;
  }

  const fallbackInviteLink =
    typeof window === "undefined"
      ? ""
      : `${window.location.origin}${window.location.pathname}?ref=${encodeURIComponent(session.referral_code)}&src=whatsapp`;

  const handleWhatsappShare = async () => {
    trackClick("share_whatsapp", {
      target: "share_whatsapp",
      role: "button",
      ctaKind: "secondary",
      payload: {
        referralCode: session.referral_code,
        referralSource: "whatsapp",
        bonusPredictionStored: true,
      },
    });
    const popup =
      typeof window === "undefined"
        ? null
        : window.open("about:blank", "_blank", "noopener,noreferrer");
    try {
      const shareUrl = await createReferralInviteLink({
        channel: "whatsapp",
        trafficSource: "whatsapp",
        trafficMedium: "social",
        campaignCode: "festival_invite_exit",
        targetPath: window.location.pathname,
      });
      const whatsappLink = `https://wa.me/?text=${encodeURIComponent(
        formatCopy(loserCopy.shareMessageTemplate, { link: shareUrl }),
      )}`;
      if (popup) {
        popup.location.href = whatsappLink;
      } else if (typeof window !== "undefined") {
        window.open(whatsappLink, "_blank", "noopener,noreferrer");
      }
    } catch {
      const fallbackWhatsappLink = `https://wa.me/?text=${encodeURIComponent(
        formatCopy(loserCopy.shareMessageTemplate, { link: fallbackInviteLink }),
      )}`;
      if (popup) {
        popup.location.href = fallbackWhatsappLink;
      } else if (typeof window !== "undefined") {
        window.open(fallbackWhatsappLink, "_blank", "noopener,noreferrer");
      }
    }
  };

  return (
    <ScreenFrame>
      <div className="sonar-screen-stack sonar-screen-stack--exit justify-between">
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
                <p className="editorial-title editorial-title--landing exit-kicker-title">
                  {loserCopy.eyebrow}
                </p>
                <h2 className="editorial-title editorial-title--compact">
                  {loserCopy.title}
                </h2>
              </div>

              <div className="sonar-panel p-5">
                <p className="editorial-body">{loserCopy.body}</p>
              </div>

              <BonusDrawPanel
                copy={bonusCopy}
                inviteStorageKey={`sonar_bonus_invite:${session.session_id}:${session.claim?.submitted_at ?? session.valid_completed_at ?? "current"}`}
                predictionValue={session.claim?.crowd_prediction_value ?? null}
                recallValue={session.claim?.social_recall_count ?? null}
                recallCorrect={session.claim?.social_recall_correct ?? null}
                showRecallQuestion={!session.is_control}
                onSelectPrediction={async (value) => {
                  await submitClaimFollowup({
                    crowd_prediction_value: value,
                  });
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
                onSaveRecall={async (value) => {
                  await submitClaimFollowup({
                    social_recall_count: value,
                  });
                  trackClick("social_recall_exit", {
                    target: "social_recall_save",
                    role: "button",
                    ctaKind: "secondary",
                    value,
                  });
                  pushTelemetry({
                    event_type: "custom",
                    event_name: "social_recall_saved",
                    screen_name: "exit",
                    value,
                    payload: {
                      session_id: session.session_id,
                      displayed_count_target: session.displayed_count_target,
                    },
                  });
                }}
              >
                <button
                  type="button"
                  onClick={() => void handleWhatsappShare()}
                  className="sonar-share-button w-full"
                >
                  {loserCopy.shareLabel}
                </button>
              </BonusDrawPanel>

              <button
                type="button"
                onClick={() => {
                  trackClick("exit_continue", {
                    target: "exit_continue",
                    role: "button",
                    ctaKind: "primary",
                  });
                  onContinueToFinal();
                }}
                className="sonar-primary-button"
              >
                {copy.common.continueLabel}
              </button>
            </>
          )}
        </div>
      </div>
    </ScreenFrame>
  );
});
