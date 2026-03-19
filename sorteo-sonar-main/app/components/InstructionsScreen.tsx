import { ScreenFrame } from "./ScreenFrame";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";
import { useSession } from "../utils/SessionContext";

interface InstructionsScreenProps {
  onContinue: () => Promise<void> | void;
}

export function InstructionsScreen({ onContinue }: InstructionsScreenProps) {
  const { publicConfig } = useSession();
  const { copy } = useLanguage();
  const { trackClick } = usePageTelemetry("instructions");
  const instructionsCopy = copy.instructions;
  const prizes = Object.entries(publicConfig.prize_eur)
    .map(([number, prize]) => ({ number: Number(number), prize }))
    .sort((left, right) => left.number - right.number);

  return (
    <ScreenFrame>
      <div className="flex min-h-full flex-col gap-8">
        <div className="space-y-4">
          <h2 className="editorial-title editorial-title--compact">
            {instructionsCopy.title}
          </h2>
          <p className="editorial-body max-w-[28rem]">
            {instructionsCopy.intro}
          </p>
          <p className="editorial-body editorial-body--muted max-w-[28rem]">
            {instructionsCopy.body}
          </p>
        </div>

        <div className="sonar-panel p-5 sm:p-6">
          <p className="editorial-eyebrow mb-4">
            {instructionsCopy.prizeTableLabel}
          </p>
          <div className="sonar-prize-grid">
            {prizes.map(({ number, prize }) => (
              <div key={number} className="sonar-prize-cell">
                <span className="sonar-prize-value">{number}</span>
                <span className="sonar-prize-amount text-slate-950">
                  {prize} {"\u20ac"}
                </span>
              </div>
            ))}
          </div>
        </div>

        <button
          onClick={() => {
            trackClick("go_to_comprehension", {
              target: "instructions_continue",
              role: "button",
              ctaKind: "primary",
            });
            void onContinue();
          }}
          className="sonar-primary-button mt-auto"
        >
          {instructionsCopy.cta}
        </button>

        <p className="editorial-micro text-center">{instructionsCopy.odds}</p>
      </div>
    </ScreenFrame>
  );
}
