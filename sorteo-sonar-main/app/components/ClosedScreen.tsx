import { memo } from "react";
import { ExperimentStatusEmailScreen } from "./ExperimentStatusEmailScreen";
import { useLanguage } from "../utils/LanguageContext";

export const ClosedScreen = memo(function ClosedScreen() {
  const { copy } = useLanguage();
  return <ExperimentStatusEmailScreen copyBlock={copy.closed} />;
});
