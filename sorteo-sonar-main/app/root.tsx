import {
  isRouteErrorResponse,
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";
import { useEffect } from "react";

import type { Route } from "./+types/root";
import "./app.css";
import criticalCss from "./critical.css?inline";
import { OfflineBanner } from "./components/OfflineBanner";
import { LanguageProvider } from "./utils/LanguageContext";
import { SessionProvider } from "./utils/SessionContext";

function ServiceWorkerResetter() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) {
      return;
    }
    void navigator.serviceWorker
      .getRegistrations()
      .then((registrations) =>
        Promise.all(registrations.map((registration) => registration.unregister())),
      )
      .catch(() => {
        // The app can continue without persistent offline support.
      });
    if (!("caches" in window)) {
      return;
    }
    void caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith("sonar-shell-"))
            .map((key) => caches.delete(key)),
        ),
      )
      .catch(() => {
        // Clearing stale shell caches is best-effort only.
      });
  }, []);

  return null;
}

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#f7f5f2" />
        <style dangerouslySetInnerHTML={{ __html: criticalCss }} />
        <Meta />
        <Links />
      </head>
      <body className="sonar-body">
        <div className="sonar-app-shell">
          <div className="sonar-app-layer">{children}</div>
        </div>
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export default function App() {
  return (
    <LanguageProvider>
      <SessionProvider>
        <ServiceWorkerResetter />
        <OfflineBanner />
        <Outlet />
      </SessionProvider>
    </LanguageProvider>
  );
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  let message = "Oops!";
  let details = "An unexpected error occurred.";
  let stack: string | undefined;

  if (isRouteErrorResponse(error)) {
    message = error.status === 404 ? "404" : "Error";
    details =
      error.status === 404
        ? "The requested page could not be found."
        : error.statusText || details;
  } else if (import.meta.env.DEV && error && error instanceof Error) {
    details = error.message;
    stack = error.stack;
  }

  return (
    <main className="container mx-auto p-4 pt-16">
      <h1>{message}</h1>
      <p>{details}</p>
      {stack && (
        <pre className="w-full overflow-x-auto p-4">
          <code>{stack}</code>
        </pre>
      )}
    </main>
  );
}
