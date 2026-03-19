import type { AppLanguage } from "../utils/uiLexicon";
import { useLanguage } from "../utils/LanguageContext";

export function LanguageSwitcher({
  variant = "compact",
  onLanguageSelected,
}: {
  variant?: "compact" | "welcome";
  onLanguageSelected?: (language: AppLanguage) => void;
}) {
  const { language, setLanguage, supportedLanguages, copy } = useLanguage();

  if (variant === "welcome") {
    return (
      <div
        role="group"
        aria-label={copy.common.languageSelectorAria}
        className="sonar-language-list"
      >
        {supportedLanguages.map((supportedLanguage) => {
          const isActive = supportedLanguage === language;
          return (
            <button
              key={supportedLanguage}
              type="button"
              onClick={() => {
                setLanguage(supportedLanguage);
                onLanguageSelected?.(supportedLanguage);
              }}
              className={`sonar-language-option ${isActive ? "is-active" : ""}`}
            >
              {copy.common.welcomeWords[supportedLanguage]}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className="sonar-language-switcher">
      <select
        value={language}
        onChange={(event) => setLanguage(event.target.value as typeof language)}
        aria-label={copy.common.languageSelectorAria}
        className="sonar-language-select"
      >
        {supportedLanguages.map((supportedLanguage) => (
          <option key={supportedLanguage} value={supportedLanguage}>
            {copy.common.languageNames[supportedLanguage]}
          </option>
        ))}
      </select>
    </div>
  );
}
