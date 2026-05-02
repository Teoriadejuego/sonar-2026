import { memo } from "react";
import { useLanguage } from "../utils/LanguageContext";
import { useSessionRuntime } from "../utils/SessionContext";

export const OfflineBanner = memo(function OfflineBanner() {
  const { copy } = useLanguage();
  const { isOnline, session } = useSessionRuntime();

  if (isOnline) {
    return null;
  }

  return (
    <div className="sonar-offline-banner" role="status" aria-live="polite">
      <div className="sonar-offline-banner__inner">
        <strong className="sonar-offline-banner__title">
          {copy.common.offlineTitle}
        </strong>
        <p className="sonar-offline-banner__body">
          {session ? copy.common.offlineBody : copy.common.offlineStartError}
        </p>
        <p className="sonar-offline-banner__hint">
          {copy.common.offlineHint}
        </p>
      </div>
    </div>
  );
});
