import { useEffect, useMemo, useRef, useState } from "react";
import { ScreenFrame } from "./ScreenFrame";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";
import { useSession } from "../utils/SessionContext";
import {
  buildPrizeRevealBoard,
  getPrizeRevealWinnerIndex,
  markPrizeRevealCompleted,
  type PrizeIconCategory,
} from "../utils/prizeReveal";
import { formatCopy } from "../utils/uiLexicon";

function PrizeRevealGlyph({ category }: { category: PrizeIconCategory }) {
  switch (category) {
    case "circle":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="prize-reveal-glyph">
          <circle cx="12" cy="12" r="6.5" fill="currentColor" />
        </svg>
      );
    case "square":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="prize-reveal-glyph">
          <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
        </svg>
      );
    case "triangle":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="prize-reveal-glyph">
          <path d="M12 5.5 18.5 17H5.5Z" fill="currentColor" />
        </svg>
      );
    case "diamond":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="prize-reveal-glyph">
          <path d="M12 4.5 19 12l-7 7-7-7Z" fill="currentColor" />
        </svg>
      );
    case "hexagon":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="prize-reveal-glyph">
          <path d="M8 5.5h8l4 6.5-4 6.5H8L4 12Z" fill="currentColor" />
        </svg>
      );
    case "star":
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" className="prize-reveal-glyph">
          <path
            d="m12 4.5 2.2 4.5 5 .7-3.6 3.4.9 4.9-4.5-2.3-4.5 2.3.9-4.9L4.8 9.7l5-.7Z"
            fill="currentColor"
          />
        </svg>
      );
  }
}

type PrizeRevealScreenProps = {
  onComplete: () => void;
};

export function PrizeRevealScreen({ onComplete }: PrizeRevealScreenProps) {
  const { session, publicConfig, pushTelemetry } = useSession();
  const { copy } = useLanguage();
  const { trackClick } = usePageTelemetry("prize_reveal");
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [winnerIndex, setWinnerIndex] = useState<number | null>(null);
  const completeTimeoutRef = useRef<number | null>(null);

  const board = useMemo(
    () => (session ? buildPrizeRevealBoard(session.session_id) : []),
    [session],
  );

  useEffect(() => {
    return () => {
      if (completeTimeoutRef.current !== null) {
        window.clearTimeout(completeTimeoutRef.current);
      }
    };
  }, []);

  if (!session) {
    return null;
  }

  const revealedPrizeAmount =
    session.claim?.reported_value != null
      ? publicConfig.prize_eur[String(session.claim.reported_value)] ?? session.payment.amount_eur
      : session.payment.amount_eur;
  const isRevealed = selectedIndex !== null && winnerIndex !== null;

  const handlePick = (index: number) => {
    if (isRevealed) {
      return;
    }

    const resolvedWinnerIndex = getPrizeRevealWinnerIndex(
      session.session_id,
      index,
      session.payment.eligible,
    );
    const pickedTile = board[index];
    const winningTile = board[resolvedWinnerIndex];

    setSelectedIndex(index);
    setWinnerIndex(resolvedWinnerIndex);

    trackClick("prize_reveal_pick", {
      target: `prize_tile_${index}`,
      role: "button",
      ctaKind: "primary",
      value: index,
      payload: {
        eligibleForPayment: session.payment.eligible,
        pickedCategory: pickedTile?.category,
        winnerCategory: winningTile?.category,
      },
    });

    pushTelemetry({
      event_type: "custom",
      event_name: "prize_reveal_resolved",
      screen_name: "prize_reveal",
      client_ts: Date.now(),
      payload: {
        selected_index: index,
        winner_index: resolvedWinnerIndex,
        selected_category: pickedTile?.category ?? null,
        winner_category: winningTile?.category ?? null,
        eligible_for_payment: session.payment.eligible,
      },
    });

    completeTimeoutRef.current = window.setTimeout(() => {
      markPrizeRevealCompleted(session.session_id, {
        selectedIndex: index,
        winnerIndex: resolvedWinnerIndex,
        completedAt: new Date().toISOString(),
      });
      onComplete();
    }, session.payment.eligible ? 1550 : 1850);
  };

  const helperText = isRevealed
    ? session.payment.eligible
      ? formatCopy(copy.prizeReveal.winnerResult, { amount: revealedPrizeAmount })
      : formatCopy(copy.prizeReveal.loserResult, { amount: revealedPrizeAmount })
    : formatCopy(copy.prizeReveal.helper, { amount: revealedPrizeAmount });

  return (
    <ScreenFrame>
      <div className="flex min-h-full flex-col gap-6">
        <div className="space-y-3 text-center">
          <p className="editorial-eyebrow">{copy.prizeReveal.eyebrow}</p>
          <h2 className="editorial-title editorial-title--compact">
            {copy.prizeReveal.title}
          </h2>
          <p className="editorial-small mx-auto max-w-[24rem]">{helperText}</p>
        </div>

        <div className="sonar-panel p-4 sm:p-5">
          <div className="prize-reveal-grid" aria-label={copy.prizeReveal.title}>
            {board.map((tile) => {
              const isPicked = selectedIndex === tile.index;
              const isWinningTile = winnerIndex === tile.index;
              const classNames = [
                "prize-reveal-cell",
                isPicked ? "prize-reveal-cell--picked" : "",
                isWinningTile ? "prize-reveal-cell--winner" : "",
                isPicked && !session.payment.eligible
                  ? "prize-reveal-cell--loser"
                  : "",
              ]
                .filter(Boolean)
                .join(" ");

              return (
                <button
                  key={`${tile.index}-${tile.category}`}
                  type="button"
                  className={classNames}
                  onClick={() => handlePick(tile.index)}
                  disabled={isRevealed}
                  aria-label={`${copy.prizeReveal.optionLabel} ${tile.index + 1}`}
                >
                  <div className="prize-reveal-face">
                    <PrizeRevealGlyph category={tile.category} />
                  </div>
                  {isWinningTile ? (
                    <div className="prize-reveal-award">
                      <span
                        className={`prize-reveal-award-amount ${
                          !session.payment.eligible
                            ? "prize-reveal-award-amount--crossed"
                            : ""
                        }`}
                      >
                        {revealedPrizeAmount} {"\u20ac"}
                      </span>
                      {!session.payment.eligible ? (
                        <span className="prize-reveal-award-cross" aria-hidden="true">
                          X
                        </span>
                      ) : null}
                    </div>
                  ) : null}
                </button>
              );
            })}
          </div>
        </div>

        {copy.prizeReveal.footer ? (
          <p className="editorial-micro text-center text-slate-500">
            {copy.prizeReveal.footer}
          </p>
        ) : null}
      </div>
    </ScreenFrame>
  );
}
