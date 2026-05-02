import {
  lazy,
  memo,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { LanguageEntryScreen } from "../components/LanguageEntryScreen";
import { ScreenFrame } from "../components/ScreenFrame";
import { WelcomeScreen } from "../components/WelcomeScreen";
import { useLanguage } from "../utils/LanguageContext";
import {
  usePublicConfig,
  useSessionActions,
  useSessionRuntime,
} from "../utils/SessionContext";
import { hasCompletedPrizeReveal } from "../utils/prizeReveal";

const loadComprehensionScreen = () =>
  import("../components/ComprehensionScreen");
const loadClosedScreen = () => import("../components/ClosedScreen");
const loadExperimentPausedScreen = () =>
  import("../components/ExperimentPausedScreen");
const loadExitScreen = () => import("../components/ExitScreen");
const loadFinalScreen = () => import("../components/FinalScreen");
const loadGameScreen = () => import("../components/GameScreen");
const loadInstructionsScreen = () =>
  import("../components/InstructionsScreen");
const loadPrizeRevealScreen = () =>
  import("../components/PrizeRevealScreen");
const loadReportScreen = () => import("../components/ReportScreen");

const ComprehensionScreen = lazy(async () => {
  const module = await loadComprehensionScreen();
  return { default: module.ComprehensionScreen };
});

const ClosedScreen = lazy(async () => {
  const module = await loadClosedScreen();
  return { default: module.ClosedScreen };
});

const ExperimentPausedScreen = lazy(async () => {
  const module = await loadExperimentPausedScreen();
  return { default: module.ExperimentPausedScreen };
});

const ExitScreen = lazy(async () => {
  const module = await loadExitScreen();
  return { default: module.ExitScreen };
});

const FinalScreen = lazy(async () => {
  const module = await loadFinalScreen();
  return { default: module.FinalScreen };
});

const GameScreen = lazy(async () => {
  const module = await loadGameScreen();
  return { default: module.GameScreen };
});

const InstructionsScreen = lazy(async () => {
  const module = await loadInstructionsScreen();
  return { default: module.InstructionsScreen };
});

const PrizeRevealScreen = lazy(async () => {
  const module = await loadPrizeRevealScreen();
  return { default: module.PrizeRevealScreen };
});

const ReportScreen = lazy(async () => {
  const module = await loadReportScreen();
  return { default: module.ReportScreen };
});

function preloadExperimentFlow() {
  return Promise.all([
    loadInstructionsScreen(),
    loadComprehensionScreen(),
    loadGameScreen(),
    loadReportScreen(),
    loadClosedScreen(),
    loadPrizeRevealScreen(),
    loadExitScreen(),
    loadFinalScreen(),
    loadExperimentPausedScreen(),
  ]);
}

const LoadingScreen = memo(function LoadingScreen({
  label,
}: {
  label: string;
}) {
  return (
    <ScreenFrame contentClassName="min-h-[calc(100%-3rem)]">
      <div className="flex min-h-full flex-col items-center justify-center gap-4 text-center">
        <div className="h-14 w-14 animate-spin rounded-full border-4 border-slate-200 border-t-slate-950" />
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">
          {label}
        </p>
      </div>
    </ScreenFrame>
  );
});

const TransitionScreen = memo(function TransitionScreen({
  title,
  label,
}: {
  title: string;
  label?: string;
}) {
  return (
    <ScreenFrame contentClassName="min-h-[calc(100%-3rem)]">
      <div className="flex min-h-full flex-col items-center justify-center gap-4 text-center">
        {label ? <p className="editorial-eyebrow">{label}</p> : null}
        <h2 className="editorial-title editorial-title--compact max-w-[18rem]">
          {title}
        </h2>
        <div className="h-14 w-14 animate-spin rounded-full border-4 border-slate-200 border-t-slate-950" />
      </div>
    </ScreenFrame>
  );
});

export function Welcome() {
  const { copy } = useLanguage();
  const [showConsentScreen, setShowConsentScreen] = useState(false);
  const [prizeRevealCompleted, setPrizeRevealCompleted] = useState(false);
  const [showFinalScreen, setShowFinalScreen] = useState(false);
  const historyGuardRef = useRef<string | null>(null);
  const publicConfig = usePublicConfig();
  const { session, displayScreen, isLoading, isHydrating, visualTransition } =
    useSessionRuntime();
  const { startSession, moveToScreen, prepareForReport } = useSessionActions();

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    if (!showConsentScreen && !session) {
      return;
    }
    const preloadTimeout = window.setTimeout(() => {
      void preloadExperimentFlow();
    }, 120);
    return () => {
      window.clearTimeout(preloadTimeout);
    };
  }, [session, showConsentScreen]);

  useEffect(() => {
    if (!displayScreen || !["report", "exit"].includes(displayScreen)) {
      historyGuardRef.current = null;
      return;
    }

    if (historyGuardRef.current === displayScreen) {
      return;
    }

    historyGuardRef.current = displayScreen;

    const safePushState = () => {
      try {
        window.history.pushState(
          { sonarScreen: displayScreen },
          document.title,
          window.location.href,
        );
      } catch {
        // iOS/WebKit can throw intermittently here; the experiment should continue.
      }
    };

    safePushState();
    const onPopState = () => {
      safePushState();
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [displayScreen]);

  useEffect(() => {
    if (!session || session.screen !== "exit") {
      setPrizeRevealCompleted(false);
      setShowFinalScreen(false);
      return;
    }
    setPrizeRevealCompleted(hasCompletedPrizeReveal(session.session_id));
  }, [session?.screen, session?.session_id]);

  const handleStart = useCallback(
    async (
      braceletId: string,
      consents: {
        ageConfirmed: boolean;
        participationAccepted: boolean;
        dataAccepted: boolean;
      },
      metrics: {
        landingVisibleMs: number;
        infoPanelsOpened: string[];
        infoPanelDurationsMs: Record<string, number>;
      },
    ) => {
      const result = await startSession(braceletId, consents, metrics);
      if (!result.success) {
        return result.error;
      }
      return null;
    },
    [startSession],
  );

  const handleContinueToComprehension = useCallback(() => {
    return moveToScreen("comprehension").catch(() => {
      // The offline banner keeps the user oriented until the request can succeed.
    });
  }, [moveToScreen]);

  const handleContinueToGame = useCallback(() => {
    return moveToScreen("game").catch(() => {
      // The offline banner keeps the user oriented until the request can succeed.
    });
  }, [moveToScreen]);

  const handleContinueToReport = useCallback(() => {
    return prepareForReport();
  }, [prepareForReport]);

  const handlePrizeRevealComplete = useCallback(() => {
    setPrizeRevealCompleted(true);
  }, []);

  const handleContinueToFinal = useCallback(() => {
    setShowFinalScreen(true);
  }, []);

  if (isHydrating) {
    return <LoadingScreen label={copy.common.loadingResume} />;
  }

  if (publicConfig.experiment_control.closed) {
    return (
      <Suspense fallback={<LoadingScreen label={copy.common.loadingPrepare} />}>
        <ClosedScreen />
      </Suspense>
    );
  }

  if (publicConfig.experiment_control.paused) {
    return (
      <Suspense fallback={<LoadingScreen label={copy.common.loadingPrepare} />}>
        <ExperimentPausedScreen />
      </Suspense>
    );
  }

  if (!session) {
    if (!showConsentScreen) {
      return (
        <LanguageEntryScreen
          onContinue={() => setShowConsentScreen(true)}
        />
      );
    }
    return <WelcomeScreen onStart={handleStart} isLoading={isLoading} />;
  }

  switch (displayScreen) {
    case "instructions":
      return (
        <Suspense fallback={<LoadingScreen label={copy.common.loadingPrepare} />}>
          <InstructionsScreen onContinue={handleContinueToComprehension} />
        </Suspense>
      );
    case "comprehension":
      return (
        <Suspense fallback={<LoadingScreen label={copy.common.loadingPrepare} />}>
          <ComprehensionScreen onPass={handleContinueToGame} />
        </Suspense>
      );
    case "game":
      return (
        <Suspense fallback={<LoadingScreen label={copy.common.loadingPrepare} />}>
          <GameScreen onContinueToReport={handleContinueToReport} />
        </Suspense>
      );
    case "report":
      return (
        <Suspense fallback={<LoadingScreen label={copy.common.loadingPrepare} />}>
          <ReportScreen onSubmitReport={() => undefined} />
        </Suspense>
      );
    case "exit":
      if (session.screen !== "exit" && visualTransition.phase === "submitting_claim") {
        return (
          <TransitionScreen
            title={copy.common.loadingPrepare}
          />
        );
      }
      return (
        <Suspense fallback={<LoadingScreen label={copy.common.loadingPrepare} />}>
          {!prizeRevealCompleted ? (
            <PrizeRevealScreen
              onComplete={handlePrizeRevealComplete}
            />
          ) : showFinalScreen ? (
            <FinalScreen
              eyebrow={copy.loser.eyebrow}
              footerText={copy.loser.bodyFooter}
              screenName="exit_final"
            />
          ) : (
            <ExitScreen onContinueToFinal={handleContinueToFinal} />
          )}
        </Suspense>
      );
    default:
      return <LoadingScreen label={copy.common.loadingPrepare} />;
  }
}
