import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "sorteo-sonar-main" / "app"


class FrontendStaticTests(unittest.TestCase):
    def read(self, *parts: str) -> str:
        return (FRONTEND.joinpath(*parts)).read_text(encoding="utf-8")

    def test_language_switcher_is_in_global_screen_frame(self) -> None:
        screen_frame = self.read("components", "ScreenFrame.tsx")
        self.assertIn("LanguageSwitcher", screen_frame)

    def test_routes_include_separate_payout_page(self) -> None:
        routes = self.read("routes.ts")
        self.assertIn('route("payout"', routes)
        self.assertIn('index("routes/home.tsx")', routes)

    def test_session_context_propagates_language_and_display_snapshots(self) -> None:
        session_context = self.read("utils", "SessionContext.tsx")
        self.assertIn("captureDisplaySnapshot", session_context)
        self.assertIn("saveDisplaySnapshot", session_context)
        self.assertIn("language,", session_context)
        self.assertIn("submitPaymentRequest", session_context)
        self.assertIn("setApiTelemetryReporter", session_context)
        self.assertIn("collectClientContext", session_context)

    def test_primary_flow_screens_use_lexicon_and_no_external_navigation(self) -> None:
        for filename in [
            ("components", "ExperimentPausedScreen.tsx"),
            ("components", "WelcomeScreen.tsx"),
            ("components", "InstructionsScreen.tsx"),
            ("components", "ComprehensionScreen.tsx"),
            ("components", "GameScreen.tsx"),
            ("components", "ReportScreen.tsx"),
        ]:
            content = self.read(*filename)
            self.assertIn("useLanguage", content)
            self.assertNotIn("http://", content)
            self.assertNotIn("https://", content)
            self.assertNotIn("wa.me", content)
            self.assertNotIn('target="_blank"', content)

    def test_welcome_route_switches_to_paused_screen_from_public_config(self) -> None:
        welcome_route = self.read("welcome", "welcome.tsx")
        self.assertIn("ExperimentPausedScreen", welcome_route)
        self.assertIn("publicConfig.experiment_control.paused", welcome_route)

    def test_winner_flow_uses_separate_payout_page_after_finish(self) -> None:
        exit_screen = self.read("components", "ExitScreen.tsx")
        self.assertIn('to={payoutPageLink}', exit_screen)
        self.assertIn("https://wa.me/?text=", exit_screen)
        self.assertIn("winner_payout_page", exit_screen)

    def test_ui_lexicon_contains_payment_page_in_all_languages(self) -> None:
        lexicon = self.read("utils", "uiLexicon.ts")
        self.assertGreaterEqual(lexicon.count("paymentPage:"), 5)
        self.assertIn("languageNames: Record<AppLanguage, string>", lexicon)
        self.assertIn('export type AppLanguage = "es" | "ca" | "en" | "fr" | "pt";', lexicon)
        self.assertIn("validateLexiconCoverage", lexicon)

    def test_frontend_has_client_context_and_spell_telemetry_utils(self) -> None:
        use_page_telemetry = self.read("utils", "usePageTelemetry.ts")
        client_context = self.read("utils", "clientContext.ts")
        self.assertIn("screen_exit", use_page_telemetry)
        self.assertIn("spellId", use_page_telemetry)
        self.assertIn("collectClientContext", client_context)
        self.assertIn("navigationEntryType", client_context)


if __name__ == "__main__":
    unittest.main()
