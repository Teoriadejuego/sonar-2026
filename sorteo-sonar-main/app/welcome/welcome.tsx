import { useEffect, useRef, useState } from "react";
import { ComprehensionScreen } from "../components/ComprehensionScreen";
import { ExperimentPausedScreen } from "../components/ExperimentPausedScreen";
import { ExitScreen } from "../components/ExitScreen";
import { FinalScreen } from "../components/FinalScreen";
import { GameScreen } from "../components/GameScreen";
import { InstructionsScreen } from "../components/InstructionsScreen";
import { LanguageEntryScreen } from "../components/LanguageEntryScreen";
import { PrizeRevealScreen } from "../components/PrizeRevealScreen";
import { ReportScreen } from "../components/ReportScreen";
import { ScreenFrame } from "../components/ScreenFrame";
import { WelcomeScreen } from "../components/WelcomeScreen";
import { useLanguage } from "../utils/LanguageContext";
import { useSession } from "../utils/SessionContext";
import { hasCompletedPrizeReveal } from "../utils/prizeReveal";

function LoadingScreen({ label }: { label: string }) {
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
}

export function Welcome() {
  const { copy } = useLanguage();
  const [showConsentScreen, setShowConsentScreen] = useState(false);
  const [prizeRevealCompleted, setPrizeRevealCompleted] = useState(false);
  const [showFinalScreen, setShowFinalScreen] = useState(false);
  const historyGuardRef = useRef<string | null>(null);
  const {
    publicConfig,
    session,
    isLoading,
    isHydrating,
    startSession,
    moveToScreen,
    prepareForReport,
  } = useSession();
  const isDemoPreview = Boolean(
    session?.session_id?.startsWith("demo-session-"),
  );

  useEffect(() => {
    if (!session || !["report", "exit"].includes(session.screen)) {
      historyGuardRef.current = null;
      return;
    }

    if (historyGuardRef.current === session.screen) {
      return;
    }

    historyGuardRef.current = session.screen;

    const safePushState = () => {
      try {
        window.history.pushState(
          { sonarScreen: session.screen },
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
  }, [session?.screen]);

  useEffect(() => {
    if (!session || session.screen !== "exit") {
      setPrizeRevealCompleted(false);
      setShowFinalScreen(false);
      return;
    }
    setPrizeRevealCompleted(hasCompletedPrizeReveal(session.session_id));
  }, [session?.screen, session?.session_id]);

  const handleStart = async (
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
  };

  if (isHydrating) {
    return <LoadingScreen label={copy.common.loadingResume} />;
  }

  if (publicConfig.experiment_control.paused && !isDemoPreview) {
    return <ExperimentPausedScreen />;
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

  switch (session.screen) {
    case "instructions":
      return (
        <InstructionsScreen onContinue={() => moveToScreen("comprehension")} />
      );
    case "comprehension":
      return <ComprehensionScreen onPass={() => moveToScreen("game")} />;
    case "game":
      return <GameScreen onContinueToReport={prepareForReport} />;
    case "report":
      return <ReportScreen onSubmitReport={() => undefined} />;
    case "exit":
      return !prizeRevealCompleted ? (
        <PrizeRevealScreen
          onComplete={() => setPrizeRevealCompleted(true)}
        />
      ) : showFinalScreen ? (
        <FinalScreen
          eyebrow={copy.loser.eyebrow}
          footerText={copy.loser.bodyFooter}
          screenName="exit_final"
        />
      ) : (
        <ExitScreen onContinueToFinal={() => setShowFinalScreen(true)} />
      );
    default:
      return <LoadingScreen label={copy.common.loadingPrepare} />;
  }
}
