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
        self.assertGreaterEqual(lexicon.count("paymentPage:"), 6)
        self.assertGreaterEqual(lexicon.count("subtitle:"), 6)
        self.assertGreaterEqual(lexicon.count("listLabel:"), 6)
        self.assertGreaterEqual(lexicon.count("steps: ["), 6)
        self.assertGreaterEqual(lexicon.count("recallTicket:"), 6)
        self.assertGreaterEqual(lexicon.count("recallPrompt:"), 6)
        self.assertGreaterEqual(lexicon.count("recallOptions:"), 6)
        self.assertGreaterEqual(lexicon.count("notAchievedLabel:"), 6)
        self.assertGreaterEqual(lexicon.count("saveError:"), 6)
        self.assertGreaterEqual(lexicon.count("finalClosingMessage:"), 6)
        self.assertGreaterEqual(lexicon.count("braceletMismatch:"), 6)
        self.assertIn("languageNames: Record<AppLanguage, string>", lexicon)
        self.assertIn('export type AppLanguage = "es" | "ca" | "en" | "fr" | "pt" | "it";', lexicon)
        self.assertIn("validateLexiconCoverage", lexicon)

    def test_demo_ids_and_new_social_message_are_wired(self) -> None:
        api_text = self.read("utils", "api.ts")
        session_context = self.read("utils", "SessionContext.tsx")
        lexicon = self.read("utils", "uiLexicon.ts")
        self.assertIn("CTRL1234", api_text)
        self.assertIn("NORM0000", api_text)
        self.assertIn("NORM0001", api_text)
        self.assertIn("design_62_treatments_v1", api_text)
        self.assertIn("{count} out of {denominator} earlier participants said they got a {target}.", lexicon)
        self.assertIn("¡Gracias por participar!", lexicon)
        self.assertIn("Tabla de premios:", lexicon)
        self.assertIn("Lanza el dado", lexicon)
        self.assertIn("¿Qué te salió en la primera tirada?", lexicon)
        self.assertIn("¿Qué número crees que nos dirá más veces la gente?", lexicon)
        self.assertIn(
            "¿Cuánta gente te dijimos que había elegido el 6 de 60 participantes anteriores?",
            lexicon,
        )
        self.assertIn("CTRL1234", session_context)
        self.assertIn("NORM0000", session_context)
        self.assertIn("NORM0001", session_context)

    def test_first_roll_capture_and_followup_wiring_are_present(self) -> None:
        game_screen = self.read("components", "GameScreen.tsx")
        dice = self.read("components", "Dice3D.tsx")
        exit_screen = self.read("components", "ExitScreen.tsx")
        bonus_draw_panel = self.read("components", "BonusDrawPanel.tsx")
        payout_page = self.read("routes", "payout.tsx")
        session_context = self.read("utils", "SessionContext.tsx")
        api_text = self.read("utils", "api.ts")

        self.assertIn("const firstResultValue = current.first_result_value ?? resultValue;", session_context)
        self.assertIn("crowd_prediction_value", api_text)
        self.assertIn("social_recall_count", api_text)
        self.assertIn("`/v1/session/${sessionId}/claim-followup`", api_text)
        self.assertIn("submitClaimFollowupRequest", session_context)
        self.assertIn("onSelectPrediction={async (value) => {", exit_screen)
        self.assertIn("onSaveRecall={async (value) => {", exit_screen)
        self.assertIn("copy.recallTicket", bonus_draw_panel)
        self.assertIn("copy.notAchievedLabel", bonus_draw_panel)
        self.assertIn('badge: recallAnsweredIncorrectly ? "0" : "+1"', bonus_draw_panel)
        self.assertIn("bonus-draw-interval-grid", bonus_draw_panel)
        self.assertIn('{ value: 20, label: copy.recallOptions[0] }', bonus_draw_panel)
        self.assertNotIn('type=\"number\"', bonus_draw_panel)
        self.assertIn("onSelectPrediction={async (value) => {", payout_page)
        self.assertIn("onSaveRecall={async (value) => {", payout_page)
        self.assertIn("recallCorrect={session.claim?.social_recall_correct ?? null}", exit_screen)
        self.assertIn("useState<number | null>(value ?? null)", dice)
        self.assertIn("Math.floor(Math.random() * 6) + 1", dice)
        self.assertIn("{isRolling ? copy.game.loading : copy.game.firstRollCta}", game_screen)

    def test_visible_exit_and_payout_copy_comes_from_lexicon(self) -> None:
        exit_screen = self.read("components", "ExitScreen.tsx")
        final_screen = self.read("components", "FinalScreen.tsx")
        payout_page = self.read("routes", "payout.tsx")

        self.assertNotIn("const CLOSING_MESSAGE", exit_screen)
        self.assertNotIn("const CLOSING_MESSAGE", payout_page)
        self.assertNotIn("const PAYOUT_BRACELET_COPY", payout_page)
        self.assertIn("copy.common.finalClosingMessage", final_screen)
        self.assertIn("copy.common.continueLabel", exit_screen)
        self.assertIn("copy.common.continueLabel", payout_page)
        self.assertIn("paymentCopy.braceletLabel", payout_page)
        self.assertIn("paymentCopy.braceletPlaceholder", payout_page)
        self.assertIn("paymentCopy.braceletRequired", payout_page)
        self.assertIn("paymentCopy.braceletMismatch", payout_page)

    def test_frontend_has_client_context_and_spell_telemetry_utils(self) -> None:
        use_page_telemetry = self.read("utils", "usePageTelemetry.ts")
        client_context = self.read("utils", "clientContext.ts")
        self.assertIn("screen_exit", use_page_telemetry)
        self.assertIn("spellId", use_page_telemetry)
        self.assertIn("collectClientContext", client_context)
        self.assertIn("navigationEntryType", client_context)


if __name__ == "__main__":
    unittest.main()
