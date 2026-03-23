import { useEffect, useRef, useState } from "react";
import { useLanguage } from "../utils/LanguageContext";

interface Dice3DProps {
  value?: number | null;
  onResult?: (result: number) => void;
  onRollRequest?: (source?: "dice" | "button" | "auto") => Promise<number>;
  onRollStart?: (source?: "dice" | "button" | "auto") => void;
  disabled?: boolean;
  interactive?: boolean;
  autoRollKey?: string | null;
  autoRollSource?: "button" | "auto";
}

export function Dice3D({
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
  const [displayValue, setDisplayValue] = useState<number>(
    () => Math.floor(Math.random() * 6) + 1,
  );
  const [isRolling, setIsRolling] = useState(false);
  const autoRollTriggeredRef = useRef<string | null>(null);

  useEffect(() => {
    if (isRolling || value == null) {
      return;
    }
    setDisplayValue(value);
  }, [isRolling, value]);

  useEffect(() => {
    if (!isRolling) {
      return;
    }
    const timer = window.setInterval(() => {
      setDisplayValue((prev) => (prev % 6) + 1);
    }, 90);
    return () => window.clearInterval(timer);
  }, [isRolling]);

  const roll = async (source: "dice" | "button" | "auto" = "dice") => {
    if (disabled || isRolling || !onRollRequest) {
      return;
    }

    setIsRolling(true);
    onRollStart?.(source);
    const startedAt = Date.now();

    try {
      const result = await onRollRequest(source);
      const elapsed = Date.now() - startedAt;
      const remaining = Math.max(0, 900 - elapsed);
      window.setTimeout(() => {
        setDisplayValue(result);
        setIsRolling(false);
        onResult?.(result);
      }, remaining);
    } catch (error) {
      console.error("[Dice] Error obteniendo resultado de API:", error);
      setIsRolling(false);
    }
  };

  const sharedClassName =
    "dice";

  useEffect(() => {
    if (!autoRollKey) {
      return;
    }
    if (autoRollTriggeredRef.current === autoRollKey) {
      return;
    }
    autoRollTriggeredRef.current = autoRollKey;
    void roll(autoRollSource);
  }, [autoRollKey, autoRollSource]);

  if (!interactive) {
    return (
      <div className={sharedClassName} aria-live="polite">
        <span className={isRolling ? "animate-pulse" : ""}>{displayValue}</span>
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
      className={`${sharedClassName} dice--interactive transition disabled:cursor-not-allowed disabled:opacity-70`}
      aria-label={copy.accessibility.diceRollAria}
    >
      <span className={isRolling ? "animate-pulse" : ""}>{displayValue}</span>
    </button>
  );
}
