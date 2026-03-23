import { type ReactNode, useEffect, useMemo, useState } from "react";
import { type UiCopy } from "../utils/uiLexicon";

interface BonusDrawPanelProps {
  copy: UiCopy["bonusDraw"];
  storageKey: string;
  inviteStorageKey?: string;
  onSelect?: (value: number) => void;
  children?: ReactNode;
}

function readStoredPrediction(storageKey: string) {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(storageKey);
  if (!raw) {
    return null;
  }
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed >= 1 && parsed <= 6 ? parsed : null;
}

export function BonusDrawPanel({
  copy,
  storageKey,
  inviteStorageKey,
  onSelect,
  children,
}: BonusDrawPanelProps) {
  const [selectedValue, setSelectedValue] = useState<number | null>(null);
  const [inviteEarned, setInviteEarned] = useState(false);
  const resolvedInviteStorageKey = inviteStorageKey ?? `${storageKey}:invite`;

  useEffect(() => {
    setSelectedValue(readStoredPrediction(storageKey));
  }, [storageKey]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    setInviteEarned(window.localStorage.getItem(resolvedInviteStorageKey) === "1");
  }, [resolvedInviteStorageKey]);

  const hasLockedPrediction = selectedValue !== null;

  const ticketRows = useMemo(
    () => [
      { badge: "1", label: copy.baseTicket, achieved: true },
      {
        badge: "+1",
        label: copy.predictionTicket,
        achieved: hasLockedPrediction,
      },
    ],
    [copy.baseTicket, copy.predictionTicket, hasLockedPrediction],
  );

  const handleSelect = (value: number) => {
    if (hasLockedPrediction) {
      return;
    }
    setSelectedValue(value);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(storageKey, String(value));
    }
    onSelect?.(value);
  };

  const handleInviteEarned = () => {
    if (inviteEarned) {
      return;
    }
    setInviteEarned(true);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(resolvedInviteStorageKey, "1");
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

      <div className="space-y-3">
        {!hasLockedPrediction ? (
          <>
            <p className="editorial-small">{copy.prompt}</p>
            <div className="bonus-draw-grid" role="group" aria-label={copy.title}>
              {[1, 2, 3, 4, 5, 6].map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => handleSelect(value)}
                  className={`bonus-draw-button ${
                    selectedValue === value ? "bonus-draw-button--selected" : ""
                  }`}
                  aria-pressed={selectedValue === value}
                >
                  {value}
                </button>
              ))}
            </div>
          </>
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
