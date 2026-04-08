import { ScreenFrame } from "./ScreenFrame";
import { useLanguage } from "../utils/LanguageContext";
import { usePageTelemetry } from "../utils/usePageTelemetry";

interface InstructionsScreenProps {
  onContinue: () => Promise<void> | void;
}

export function InstructionsScreen({ onContinue }: InstructionsScreenProps) {
  const { copy } = useLanguage();
  const { trackClick } = usePageTelemetry("instructions");
  const instructionsCopy = copy.instructions;

  return (
    <ScreenFrame>
      <div className="sonar-screen-stack sonar-screen-stack--instructions">
        <div className="instructions-hero">
          <h2 className="editorial-title editorial-title--compact instructions-title">
            {instructionsCopy.title}
          </h2>
          <p className="editorial-body instructions-subtitle">
            {instructionsCopy.subtitle}
          </p>
        </div>

        <div className="sonar-panel sonar-panel-subtle instructions-panel">
          <p className="editorial-body editorial-body--muted instructions-label">
            {instructionsCopy.listLabel}
          </p>
          <ol className="sonar-instructions-list">
            {instructionsCopy.steps.map((step) => (
              <li key={step} className="sonar-instructions-item">
                {step}
              </li>
            ))}
          </ol>
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

        {instructionsCopy.odds ? (
          <p className="editorial-micro text-center">{instructionsCopy.odds}</p>
        ) : null}
      </div>
    </ScreenFrame>
  );
}
