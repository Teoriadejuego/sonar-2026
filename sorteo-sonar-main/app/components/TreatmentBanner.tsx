import type { ReportSnapshot } from "../utils/api";
import { useLanguage } from "../utils/LanguageContext";
import { formatCopy } from "../utils/uiLexicon";

export function TreatmentBanner({ snapshot }: { snapshot: ReportSnapshot }) {
  const { copy } = useLanguage();

  if (snapshot.is_control) {
    return (
      <div className="sonar-panel w-full p-5 text-left">
        <p className="editorial-body font-semibold text-slate-900">
          {copy.treatment.controlTitle}
        </p>
        <p className="editorial-body mt-1 font-semibold text-slate-900">
          {copy.treatment.controlBody}
        </p>
      </div>
    );
  }

  return (
    <div className="sonar-panel sonar-panel-highlight w-full p-5 text-left">
      <p className="text-[clamp(1.5rem,5.6vw,2.15rem)] font-black leading-[1.05] tracking-tight text-slate-950">
        {formatCopy(copy.treatment.socialMessageTemplate, {
          count: snapshot.count_target ?? "-",
          denominator: snapshot.denominator ?? "-",
          target: snapshot.target_value ?? "-",
        })}
      </p>
    </div>
  );
}
