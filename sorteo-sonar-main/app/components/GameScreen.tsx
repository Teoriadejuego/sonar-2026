import { memo, useCallback, useEffect, useRef, useState } from "react";
import { Dice3D } from "./Dice3D";
import { ScreenFrame } from "./ScreenFrame";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";
import {
  DeferredRecoveryError,
  useSessionActions,
  useSessionRuntime,
} from "../utils/SessionContext";
import { formatCopy, translateServerError } from "../utils/uiLexicon";

interface GameScreenProps {
  onContinueToReport: () => Promise<void>;
}

export const GameScreen = memo(function GameScreen({
  onContinueToReport,
}: GameScreenProps) {
  const { session, networkRecovery } = useSessionRuntime();
  const { rollNext, pushTelemetry } = useSessionActions();
  const { copy } = useLanguage();
  const { trackClick } = usePageTelemetry("game");
  const [isRolling, setIsRolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPreparing, setIsPreparing] = useState(false);
  const [buttonRollKey, setButtonRollKey] = useState<string | null>(null);
  const [buttonRollKind, setButtonRollKind] = useState<"first_roll" | "reroll">(
    "first_roll",
  );
  const enteredAtRef = useRef(Date.now());
  const sessionId = session?.session_id ?? "";
  const isRollRecovering =
    networkRecovery.phase === "retrying" && networkRecovery.action === "roll";
  const isPrepareRecovering =
    networkRecovery.phase === "retrying" &&
    networkRecovery.action === "prepare_report";
  const recoveryMessage =
    isRollRecovering || isPrepareRecovering ? networkRecovery.message : null;

  const handleRollVisualStart = useCallback(() => {
    setError(null);
    setIsRolling(true);
  }, []);

  const handleRollVisualResolved = useCallback(() => {
    setIsRolling(false);
    setButtonRollKey(null);
    enteredAtRef.current = Date.now();
  }, []);

  const handleRoll = useCallback(
    async (
      kind: "first_roll" | "reroll",
      trigger: "dice" | "button" | "auto",
    ): Promise<number> => {
      if (!session) {
        throw new Error(copy.game.errors.noSession);
      }
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
        return result;
      } catch (err) {
        setIsRolling(false);
        setButtonRollKey(null);
        if (err instanceof DeferredRecoveryError) {
          setError(null);
          throw err;
        }
        setError(
          err instanceof Error
            ? translateServerError(err.message, copy)
            : copy.game.errors.loadRoll,
        );
        throw err;
      }
    },
    [copy.game.errors.loadRoll, copy.game.errors.noSession, pushTelemetry, rollNext, session, trackClick],
  );

  useEffect(() => {
    enteredAtRef.current = Date.now();
    setButtonRollKey(null);
    setButtonRollKind("first_roll");
  }, [sessionId]);

  const triggerRollFromButton = useCallback((kind: "first_roll" | "reroll") => {
    if (
      !session ||
      isRolling ||
      isPreparing ||
      buttonRollKey !== null ||
      (kind === "first_roll" && session.first_result_value !== null)
    ) {
      return;
    }
    setError(null);
    setButtonRollKind(kind);
    setButtonRollKey(`${session.session_id}:${Date.now()}`);
  }, [buttonRollKey, isPreparing, isRolling, session]);

  const handleContinue = useCallback(async () => {
    try {
      setIsPreparing(true);
      trackClick("go_to_report", {
        target: "continue_to_report",
        role: "button",
        ctaKind: "primary",
      });
      await onContinueToReport();
    } catch (err) {
      if (err instanceof DeferredRecoveryError) {
        setError(null);
        return;
      }
      setError(
        err instanceof Error
          ? translateServerError(err.message, copy)
          : copy.game.errors.loadReport,
      );
    } finally {
      setIsPreparing(false);
    }
  }, [copy, onContinueToReport, trackClick]);

  const handleAutoRollRequest = useCallback(
    (source?: "dice" | "button" | "auto") =>
      handleRoll(buttonRollKind, source ?? "button"),
    [buttonRollKind, handleRoll],
  );

  if (!session) {
    return null;
  }

  const hasCommittedFirstRoll = session.first_result_value !== null;
  const hasSettledFirstRoll = hasCommittedFirstRoll && !isRolling;
  const isRollPending = isRolling || isRollRecovering || buttonRollKey !== null;
  const lastThrow = session.throws[session.throws.length - 1];
  const currentVisibleValue =
    lastThrow?.result_value ?? session.last_seen_value ?? null;
  const showDice = hasCommittedFirstRoll || isRolling || buttonRollKey !== null;
  const canReroll = session.throws.length > 0 && session.throws.length < session.max_attempts;

  return (
    <ScreenFrame>
      <div className="sonar-screen-stack sonar-screen-stack--game">
        <div className="space-y-3 text-center">
          <h2 className="editorial-title editorial-title--compact">
            {copy.game.title}
          </h2>
          {!hasCommittedFirstRoll && copy.game.initialIntro ? (
            <p className="editorial-small mx-auto max-w-[22rem]">
              {copy.game.initialIntro}
            </p>
          ) : null}
        </div>

        {!showDice ? (
          <div className="dice-launch-idle">
            <button
              onClick={() => triggerRollFromButton("first_roll")}
              disabled={isRollPending || isPrepareRecovering}
              className="sonar-primary-button sonar-primary-button--hero"
            >
              {isRollPending ? copy.game.loading : copy.game.firstRollCta}
            </button>
          </div>
        ) : (
          <div className="dice-launch-panel">
            <div className="dice-launch-canvas">
              <Dice3D
                value={currentVisibleValue}
                interactive={false}
                disabled={isPreparing}
                autoRollKey={buttonRollKey}
                autoRollSource="button"
                onRollStart={handleRollVisualStart}
                onResult={handleRollVisualResolved}
                onRollRequest={handleAutoRollRequest}
              />
            </div>

            {hasSettledFirstRoll && session.first_result_value !== null ? (
              <div className="dice-result-strip">
                <p className="editorial-small text-slate-950">
                  {formatCopy(copy.game.firstResultTemplate, {
                    value: session.first_result_value,
                  })}
                </p>
                {session.throws.length > 1 ? (
                  <p className="editorial-micro text-slate-600">
                    {formatCopy(copy.game.attemptsTemplate, {
                      count: session.throws.length,
                    })}
                  </p>
                ) : null}
              </div>
            ) : null}

            <div className="dice-action-stack">
              {!hasSettledFirstRoll ? (
                <button
                  onClick={() => triggerRollFromButton("first_roll")}
                  disabled={isRollPending || isPrepareRecovering}
                  className="sonar-primary-button sonar-primary-button--hero"
                >
                  {isRollPending ? copy.game.loading : copy.game.firstRollCta}
                </button>
              ) : (
                <>
                  {canReroll ? (
                    <button
                      onClick={() => triggerRollFromButton("reroll")}
                      disabled={isRollPending || isPreparing || isPrepareRecovering}
                      className="sonar-secondary-button w-full"
                    >
                      {isRollPending ? copy.game.loading : copy.game.rerollCta}
                    </button>
                  ) : null}
                  <button
                    onClick={() => void handleContinue()}
                    disabled={isRolling || isPreparing || isPrepareRecovering}
                    className="sonar-primary-button"
                  >
                    {copy.game.continueCta}
                  </button>
                </>
              )}
            </div>
          </div>
        )}

        {recoveryMessage ? (
          <div className="sonar-status" aria-live="polite">
            {recoveryMessage}
          </div>
        ) : null}

        {error && !recoveryMessage && (
          <div className="sonar-status sonar-panel-danger">
            {error}
          </div>
        )}
      </div>
    </ScreenFrame>
  );
});
