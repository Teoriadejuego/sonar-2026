import { ScreenFrame } from "./ScreenFrame";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";
import { useSession } from "../utils/SessionContext";

interface ComprehensionScreenProps {
  onPass: () => Promise<void> | void;
}

export function ComprehensionScreen({ onPass }: ComprehensionScreenProps) {
  const { copy } = useLanguage();
  const { publicConfig } = useSession();
  const { trackClick } = usePageTelemetry("comprehension");
  const comprehensionCopy = copy.comprehension;
  const prizes = Object.entries(publicConfig.prize_eur)
    .map(([number, prize]) => ({ number: Number(number), prize }))
    .sort((left, right) => left.number - right.number);

  return (
    <ScreenFrame>
      <div className="sonar-screen-stack">
        <div className="space-y-4">
          {comprehensionCopy.eyebrow ? (
            <p className="editorial-eyebrow">{comprehensionCopy.eyebrow}</p>
          ) : null}
          <h2 className="editorial-title editorial-title--compact max-w-[22rem]">
            {comprehensionCopy.title}
          </h2>
          <p className="editorial-body max-w-[28rem]">
            {comprehensionCopy.body}
          </p>
          <p className="editorial-small max-w-[28rem]">
            {comprehensionCopy.odds}
          </p>
        </div>

        <div className="sonar-panel p-5 sm:p-6">
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
          type="button"
          onClick={() => {
            trackClick("go_to_game", {
              target: "comprehension_continue",
              role: "button",
              ctaKind: "primary",
            });
            void onPass();
          }}
          className="sonar-primary-button mt-auto"
        >
          {comprehensionCopy.cta}
        </button>
      </div>
    </ScreenFrame>
  );
}
