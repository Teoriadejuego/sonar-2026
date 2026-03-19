import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  SUPPORTED_LANGUAGES,
  UI_LEXICON,
  type AppLanguage,
  type UiCopy,
} from "./uiLexicon";

type LanguageContextValue = {
  language: AppLanguage;
  setLanguage: (language: AppLanguage) => void;
  copy: UiCopy;
  supportedLanguages: AppLanguage[];
};

const LANGUAGE_STORAGE_KEY = "sonar_language_v1";

const LanguageContext = createContext<LanguageContextValue | undefined>(
  undefined,
);

function readStoredLanguage(): AppLanguage {
  if (typeof window === "undefined") {
    return "es";
  }
  const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (stored && SUPPORTED_LANGUAGES.includes(stored as AppLanguage)) {
    return stored as AppLanguage;
  }
  return "es";
}

export function LanguageProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [language, setLanguageState] = useState<AppLanguage>(readStoredLanguage);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    document.documentElement.lang = language;
    document.title = UI_LEXICON[language].common.appTitle;
    window.dispatchEvent(
      new CustomEvent("sonar_language_changed", {
        detail: {
          language,
          changedAt: Date.now(),
        },
      }),
    );
  }, [language]);

  const value = useMemo<LanguageContextValue>(
    () => ({
      language,
      setLanguage: setLanguageState,
      copy: UI_LEXICON[language],
      supportedLanguages: SUPPORTED_LANGUAGES,
    }),
    [language],
  );

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within LanguageProvider");
  }
  return context;
}
