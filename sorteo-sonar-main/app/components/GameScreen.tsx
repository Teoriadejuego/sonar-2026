import { useEffect, useRef, useState } from "react";
import { Dice3D } from "./Dice3D";
import { ScreenFrame } from "./ScreenFrame";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";
import { useSession } from "../utils/SessionContext";
import { formatCopy, translateServerError } from "../utils/uiLexicon";

interface GameScreenProps {
  onContinueToReport: () => Promise<void>;
}

export function GameScreen({ onContinueToReport }: GameScreenProps) {
  const { session, rollNext, pushTelemetry } = useSession();
  const { copy } = useLanguage();
  const { trackClick } = usePageTelemetry("game");
  const [isRolling, setIsRolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPreparing, setIsPreparing] = useState(false);
  const [buttonRollKey, setButtonRollKey] = useState<string | null>(null);
  const enteredAtRef = useRef(Date.now());

  const handleRoll = async (
    kind: "first_roll" | "reroll",
    trigger: "dice" | "button" | "auto",
  ): Promise<number> => {
    if (!session) {
      throw new Error(copy.game.errors.noSession);
    }
    setError(null);
    setIsRolling(true);
    const reactionMs = Date.now() - enteredAtRef.current;
    trackClick(kind === "first_roll" ? "first_roll_cta" : "reroll_cta", {
      target:
        trigger === "dice"
          ? "dice_surface"
          : trigger === "auto"
            ? `${kind}_auto`
            : `${kind}_button`,
      role: "button",
      ctaKind: kind === "first_roll" ? "primary" : "secondary",
      payload: {
        reactionMs,
        attemptIndex: session.throws.length + 1,
        trigger,
      },
    });

    try {
      const result = await rollNext(reactionMs);
      pushTelemetry({
        event_type: "custom",
        event_name: kind,
        screen_name: "game",
        client_ts: Date.now(),
        duration_ms: reactionMs,
        value: result,
      });
      enteredAtRef.current = Date.now();
      return result;
    } catch (err) {
      setError(
        err instanceof Error
          ? translateServerError(err.message, copy)
          : copy.game.errors.loadRoll,
      );
      throw err;
    } finally {
      setIsRolling(false);
    }
  };

  if (!session) {
    return null;
  }

  const hasFirstRoll = session.first_result_value !== null;
  const lastThrow = session.throws[session.throws.length - 1];
  const currentVisibleValue = lastThrow?.result_value ?? session.last_seen_value ?? null;
  const canLaunch = !isPreparing && !hasFirstRoll;
  const showDice = hasFirstRoll || isRolling || buttonRollKey !== null;

  useEffect(() => {
    enteredAtRef.current = Date.now();
  }, [session.session_id]);

  const triggerRollFromButton = () => {
    if (isRolling || isPreparing || !canLaunch) {
      return;
    }
    setButtonRollKey(`${session.session_id}:${Date.now()}`);
  };

  return (
    <ScreenFrame>
      <div className="sonar-screen-stack sonar-screen-stack--game">
        <div className="space-y-3 text-center">
          <h2 className="editorial-title editorial-title--compact">
            {copy.game.title}
          </h2>
          {!hasFirstRoll && copy.game.initialIntro ? (
            <p className="editorial-small mx-auto max-w-[22rem]">
              {copy.game.initialIntro}
            </p>
          ) : null}
        </div>

        {!showDice ? (
          <div className="dice-launch-idle">
            <button
              onClick={triggerRollFromButton}
              disabled={isRolling}
              className="sonar-primary-button sonar-primary-button--hero"
            >
              {isRolling ? copy.game.loading : copy.game.firstRollCta}
            </button>
          </div>
        ) : (
          <div className="dice-launch-panel">
            <div className="dice-launch-canvas">
              <Dice3D
                value={currentVisibleValue}
                interactive={false}
                disabled={isRolling || isPreparing}
                autoRollKey={buttonRollKey}
                autoRollSource="button"
                onRollRequest={(source) => handleRoll("first_roll", source ?? "button")}
              />
            </div>

            {hasFirstRoll && session.first_result_value !== null ? (
              <div className="dice-result-strip">
                <p className="editorial-small text-slate-950">
                  {formatCopy(copy.game.firstResultTemplate, {
                    value: session.first_result_value,
                  })}
                </p>
              </div>
            ) : null}

            <div className="dice-action-stack">
              {!hasFirstRoll ? (
                <button
                  onClick={triggerRollFromButton}
                  disabled={isRolling}
                  className="sonar-primary-button sonar-primary-button--hero"
                >
                  {isRolling ? copy.game.loading : copy.game.firstRollCta}
                </button>
              ) : (
                <button
                  onClick={async () => {
                    try {
                      setIsPreparing(true);
                      trackClick("go_to_report", {
                        target: "continue_to_report",
                        role: "button",
                        ctaKind: "primary",
                      });
                      await onContinueToReport();
                    } catch (err) {
                      setError(
                        err instanceof Error
                          ? translateServerError(err.message, copy)
                          : copy.game.errors.loadReport,
                      );
                    } finally {
                      setIsPreparing(false);
                    }
                  }}
                  disabled={isRolling || isPreparing}
                  className="sonar-primary-button"
                >
                  {copy.game.continueCta}
                </button>
              )}
            </div>
          </div>
        )}

        {error && (
          <div className="sonar-status sonar-panel-danger">
            {error}
          </div>
        )}
      </div>
    </ScreenFrame>
  );
}
