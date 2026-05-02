import { reactRouter } from "@react-router/dev/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  envPrefix: ["VITE_", "API_"],
  plugins: [tailwindcss(), reactRouter(), tsconfigPaths()],
  build: {
    cssCodeSplit: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          const normalizedId = id.replace(/\\/g, "/");

          if (normalizedId.includes("/node_modules/")) {
            if (
              normalizedId.includes("/react/") ||
              normalizedId.includes("/react-dom/") ||
              normalizedId.includes("/react-router/")
            ) {
              return "react-vendor";
            }
            return "vendor";
          }

          if (
            normalizedId.includes("/app/utils/SessionContext.tsx") ||
            normalizedId.includes("/app/utils/api.ts") ||
            normalizedId.includes("/app/utils/telemetryQueue.ts") ||
            normalizedId.includes("/app/utils/clientContext.ts")
          ) {
            return "session-runtime";
          }

          if (
            normalizedId.includes("/app/components/InstructionsScreen.tsx") ||
            normalizedId.includes("/app/components/ComprehensionScreen.tsx") ||
            normalizedId.includes("/app/components/GameScreen.tsx") ||
            normalizedId.includes("/app/components/ReportScreen.tsx") ||
            normalizedId.includes("/app/components/PrizeRevealScreen.tsx") ||
            normalizedId.includes("/app/components/ExitScreen.tsx") ||
            normalizedId.includes("/app/components/FinalScreen.tsx") ||
            normalizedId.includes("/app/components/ExperimentPausedScreen.tsx") ||
            normalizedId.includes("/app/utils/prizeReveal.ts")
          ) {
            return "experiment-flow";
          }
        },
      },
    },
  },
});
