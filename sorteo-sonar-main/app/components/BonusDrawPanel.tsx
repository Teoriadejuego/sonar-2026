import { type ReactNode, useEffect, useMemo, useState } from "react";
import { type UiCopy } from "../utils/uiLexicon";

interface BonusDrawPanelProps {
  copy: UiCopy["bonusDraw"];
  inviteStorageKey: string;
  predictionValue?: number | null;
  recallValue?: number | null;
  showRecallQuestion?: boolean;
  onSelectPrediction?: (value: number) => Promise<void> | void;
  onSaveRecall?: (value: number) => Promise<void> | void;
  children?: ReactNode;
}

function readInviteEarned(storageKey: string) {
  if (typeof window === "undefined") {
    return false;
  }
  return window.localStorage.getItem(storageKey) === "1";
}

function normalizeRecallBucket(value: number | null) {
  if (value === null) {
    return null;
  }
  if (value <= 20) {
    return 20;
  }
  if (value <= 40) {
    return 40;
  }
  return 60;
}

export function BonusDrawPanel({
  copy,
  inviteStorageKey,
  predictionValue = null,
  recallValue = null,
  showRecallQuestion = false,
  onSelectPrediction,
  onSaveRecall,
  children,
}: BonusDrawPanelProps) {
  const [selectedValue, setSelectedValue] = useState<number | null>(predictionValue);
  const [savedRecallValue, setSavedRecallValue] = useState<number | null>(recallValue);
  const [inviteEarned, setInviteEarned] = useState(false);
  const [isSavingPrediction, setIsSavingPrediction] = useState(false);
  const [isSavingRecall, setIsSavingRecall] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSelectedValue(predictionValue);
  }, [predictionValue]);

  useEffect(() => {
    setSavedRecallValue(recallValue);
  }, [recallValue]);

  useEffect(() => {
    setInviteEarned(readInviteEarned(inviteStorageKey));
  }, [inviteStorageKey]);

  const hasLockedPrediction = selectedValue !== null;
  const hasSavedRecall = savedRecallValue !== null;
  const recallOptions = useMemo(
    () => [
      { value: 20, label: copy.recallOptions[0] },
      { value: 40, label: copy.recallOptions[1] },
      { value: 60, label: copy.recallOptions[2] },
    ],
    [copy.recallOptions],
  );
  const savedRecallBucket = normalizeRecallBucket(savedRecallValue);

  const ticketRows = useMemo(
    () =>
      [
        { badge: "1", label: copy.baseTicket, achieved: true },
        {
          badge: "+1",
          label: copy.predictionTicket,
          achieved: hasLockedPrediction,
        },
        showRecallQuestion
          ? {
              badge: "+1",
              label: copy.recallTicket,
              achieved: hasSavedRecall,
            }
          : null,
      ].filter(Boolean) as Array<{
        badge: string;
        label: string;
        achieved: boolean;
      }>,
    [
      copy.baseTicket,
      copy.predictionTicket,
      copy.recallTicket,
      hasLockedPrediction,
      hasSavedRecall,
      showRecallQuestion,
    ],
  );

  const handleSelect = async (value: number) => {
    if (hasLockedPrediction || isSavingPrediction) {
      return;
    }
    const previousValue = selectedValue;
    setError(null);
    setSelectedValue(value);
    setIsSavingPrediction(true);
    try {
      await onSelectPrediction?.(value);
    } catch {
      setSelectedValue(previousValue);
      setError(copy.saveError);
    } finally {
      setIsSavingPrediction(false);
    }
  };

  const handleSaveRecall = async (value: number) => {
    if (savedRecallValue !== null || isSavingRecall) {
      return;
    }

    setError(null);
    setIsSavingRecall(true);
    try {
      await onSaveRecall?.(value);
      setSavedRecallValue(value);
    } catch {
      setError(copy.saveError);
    } finally {
      setIsSavingRecall(false);
    }
  };

  const handleInviteEarned = () => {
    if (inviteEarned) {
      return;
    }
    setInviteEarned(true);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(inviteStorageKey, "1");
    }
  };

  return (
    <div className="bonus-draw-panel">
      <div className="space-y-2">
        <p className="editorial-small font-semibold text-slate-950">
          {copy.title}
        </p>
        <p className="editorial-small">{copy.intro}</p>
      </div>

      <div className="bonus-draw-ticket-list">
        {ticketRows.map((item) => (
          <div
            key={`${item.badge}-${item.label}`}
            className={`bonus-draw-ticket-item ${
              item.achieved ? "bonus-draw-ticket-item--achieved" : ""
            }`}
          >
            <span className="bonus-draw-ticket-badge">{item.badge}</span>
            <span className="bonus-draw-ticket-text">{item.label}</span>
            {item.achieved ? (
              <span className="bonus-draw-ticket-state">{copy.achievedLabel}</span>
            ) : null}
          </div>
        ))}
      </div>

      <div className="space-y-4">
        {!hasLockedPrediction ? (
          <div className="space-y-3">
            <p className="editorial-small">{copy.prompt}</p>
            <div className="bonus-draw-grid" role="group" aria-label={copy.title}>
              {[1, 2, 3, 4, 5, 6].map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => void handleSelect(value)}
                  disabled={isSavingPrediction}
                  className={`bonus-draw-button ${
                    selectedValue === value ? "bonus-draw-button--selected" : ""
                  }`}
                  aria-pressed={selectedValue === value}
                >
                  {value}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {showRecallQuestion && !hasSavedRecall ? (
          <div className="space-y-3">
            <p className="editorial-small">{copy.recallPrompt}</p>
            <div
              className="bonus-draw-interval-grid"
              role="group"
              aria-label={copy.recallPrompt}
            >
              {recallOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => void handleSaveRecall(option.value)}
                  disabled={isSavingRecall}
                  className={`bonus-draw-button bonus-draw-button--interval ${
                    savedRecallBucket === option.value
                      ? "bonus-draw-button--selected"
                      : ""
                  }`}
                  aria-pressed={savedRecallBucket === option.value}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {error ? (
          <div className="sonar-status sonar-panel-danger">
            {error}
          </div>
        ) : null}

        <div
          className={`bonus-draw-ticket-item bonus-draw-ticket-item--invite ${
            inviteEarned ? "bonus-draw-ticket-item--achieved" : ""
          }`}
        >
          <span className="bonus-draw-ticket-badge">+1</span>
          <span className="bonus-draw-ticket-text">{copy.inviteTicket}</span>
          {inviteEarned ? (
            <span className="bonus-draw-ticket-state">{copy.achievedLabel}</span>
          ) : null}
        </div>

        {children ? (
          <div onClickCapture={handleInviteEarned}>
            {children}
          </div>
        ) : null}
      </div>
    </div>
  );
}
