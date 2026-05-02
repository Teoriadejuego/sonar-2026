import {
  memo,
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { useLanguage } from "../utils/LanguageContext";

type RollSource = "dice" | "button" | "auto";

interface Dice3DProps {
  value?: number | null;
  onResult?: (result: number) => void;
  onRollRequest?: (source?: RollSource) => Promise<number>;
  onRollStart?: (source?: RollSource) => void;
  disabled?: boolean;
  interactive?: boolean;
  autoRollKey?: string | null;
  autoRollSource?: "button" | "auto";
}

type RollPhase = "idle" | "rolling" | "awaiting";

type DiceMotionStyle = CSSProperties & {
  "--dice-roll-x"?: string;
  "--dice-roll-y"?: string;
  "--dice-roll-z"?: string;
  "--dice-roll-lift"?: string;
  "--dice-roll-squash"?: string;
};

const ROLL_VISUAL_DURATION_MS = 760;
const ROLL_VARIANTS: readonly DiceMotionStyle[] = [
  {
    "--dice-roll-x": "1.35turn",
    "--dice-roll-y": "0.9turn",
    "--dice-roll-z": "0.24turn",
    "--dice-roll-lift": "-18px",
    "--dice-roll-squash": "0.9",
  },
  {
    "--dice-roll-x": "1.12turn",
    "--dice-roll-y": "1.15turn",
    "--dice-roll-z": "0.42turn",
    "--dice-roll-lift": "-15px",
    "--dice-roll-squash": "0.92",
  },
  {
    "--dice-roll-x": "1.58turn",
    "--dice-roll-y": "0.7turn",
    "--dice-roll-z": "0.18turn",
    "--dice-roll-lift": "-21px",
    "--dice-roll-squash": "0.88",
  },
];

function getRollStyle(index: number): DiceMotionStyle {
  return ROLL_VARIANTS[index % ROLL_VARIANTS.length];
}

export const Dice3D = memo(function Dice3D({
  value,
  onResult,
  onRollRequest,
  onRollStart,
  disabled = false,
  interactive = true,
  autoRollKey = null,
  autoRollSource = "auto",
}: Dice3DProps) {
  const { copy } = useLanguage();
  const [displayValue, setDisplayValue] = useState<number | null>(value ?? null);
  const [rollPhase, setRollPhase] = useState<RollPhase>("idle");
  const [rollStyle, setRollStyle] = useState<DiceMotionStyle>(() =>
    getRollStyle(0),
  );
  const autoRollTriggeredRef = useRef<string | null>(null);
  const settleTimeoutRef = useRef<number | null>(null);
  const pendingResultRef = useRef<number | null>(null);
  const latestResolvedValueRef = useRef<number | null>(value ?? null);
  const rollCycleRef = useRef(0);
  const activeRollIdRef = useRef(0);

  const clearSettleTimeout = useCallback(() => {
    if (settleTimeoutRef.current !== null) {
      window.clearTimeout(settleTimeoutRef.current);
      settleTimeoutRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (rollPhase !== "idle" || value == null) {
      return;
    }
    latestResolvedValueRef.current = value;
    setDisplayValue(value);
  }, [rollPhase, value]);

  useEffect(() => {
    if (value == null && rollPhase === "idle") {
      latestResolvedValueRef.current = null;
      setDisplayValue(null);
    }
  }, [rollPhase, value]);

  useEffect(() => {
    return () => {
      clearSettleTimeout();
      pendingResultRef.current = null;
      activeRollIdRef.current += 1;
    };
  }, [clearSettleTimeout]);

  const finalizeRoll = useCallback(
    (result: number) => {
      clearSettleTimeout();
      pendingResultRef.current = null;
      latestResolvedValueRef.current = result;
      setDisplayValue(result);
      setRollPhase("idle");
      onResult?.(result);
    },
    [clearSettleTimeout, onResult],
  );

  const failRoll = useCallback(() => {
    clearSettleTimeout();
    pendingResultRef.current = null;
    setDisplayValue(latestResolvedValueRef.current);
    setRollPhase("idle");
  }, [clearSettleTimeout]);

  const startVisualRoll = useCallback(() => {
    clearSettleTimeout();
    pendingResultRef.current = null;
    setRollStyle(getRollStyle(rollCycleRef.current));
    rollCycleRef.current += 1;
    setDisplayValue(null);
    setRollPhase("rolling");
    settleTimeoutRef.current = window.setTimeout(() => {
      settleTimeoutRef.current = null;
      const pendingResult = pendingResultRef.current;
      if (pendingResult == null) {
        setRollPhase("awaiting");
        return;
      }
      finalizeRoll(pendingResult);
    }, ROLL_VISUAL_DURATION_MS);
  }, [clearSettleTimeout, finalizeRoll]);

  const roll = useCallback(
    async (source: RollSource = "dice") => {
      if (disabled || rollPhase !== "idle" || !onRollRequest) {
        return;
      }

      const rollId = activeRollIdRef.current + 1;
      activeRollIdRef.current = rollId;
      onRollStart?.(source);
      startVisualRoll();

      try {
        const result = await onRollRequest(source);
        if (activeRollIdRef.current !== rollId) {
          return;
        }
        if (settleTimeoutRef.current !== null) {
          pendingResultRef.current = result;
          return;
        }
        finalizeRoll(result);
      } catch (error) {
        if (activeRollIdRef.current !== rollId) {
          return;
        }
        console.error("[Dice] Error obteniendo resultado de API:", error);
        failRoll();
      }
    },
    [
      disabled,
      failRoll,
      finalizeRoll,
      onRollRequest,
      onRollStart,
      rollPhase,
      startVisualRoll,
    ],
  );

  const isBusy = rollPhase !== "idle";
  const sharedClassName = [
    "dice",
    interactive ? "dice--interactive" : "",
    displayValue == null && !isBusy ? "dice--empty" : "dice--resolved",
    rollPhase === "rolling" ? "dice--rolling" : "",
    rollPhase === "awaiting" ? "dice--awaiting" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const glyphClassName = [
    "dice__glyph",
    isBusy ? "dice__glyph--hidden" : "",
  ]
    .filter(Boolean)
    .join(" ");

  useEffect(() => {
    if (!autoRollKey) {
      return;
    }
    if (autoRollTriggeredRef.current === autoRollKey) {
      return;
    }
    autoRollTriggeredRef.current = autoRollKey;
    void roll(autoRollSource);
  }, [autoRollKey, autoRollSource, roll]);

  if (!interactive) {
    return (
      <div
        className={sharedClassName}
        style={rollStyle}
        aria-live="polite"
        aria-busy={isBusy}
      >
        <span className={glyphClassName}>
          {displayValue == null ? "\u00A0" : String(displayValue)}
        </span>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => void roll("dice")}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          void roll("dice");
        }
      }}
      disabled={disabled || !onRollRequest}
      style={rollStyle}
      className={`${sharedClassName} transition disabled:cursor-not-allowed disabled:opacity-70`}
      aria-label={copy.accessibility.diceRollAria}
      aria-busy={isBusy}
    >
      <span className={glyphClassName}>
        {displayValue == null ? "\u00A0" : String(displayValue)}
      </span>
    </button>
  );
});
