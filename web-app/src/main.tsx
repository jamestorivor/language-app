import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { LanguageProvider } from "./i18n";
import { BrowserRouter } from "react-router";
import { ClerkProvider, SignIn, UserButton, useAuth } from "@clerk/react";
import { setSessionTokenProvider } from "./api/client";

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

function AuthenticationGate() {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  setSessionTokenProvider(isSignedIn ? getToken : undefined);
  if (!isLoaded) return <p className="p-8">Loading account…</p>;
  if (!isSignedIn) return <main className="min-h-screen grid place-items-center bg-[#f7f7f4] p-6"><SignIn routing="hash" /></main>;
  return <App accountControl={<UserButton />} />;
}

if (!publishableKey) throw new Error("Set VITE_CLERK_PUBLISHABLE_KEY to enable sign-in");

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ClerkProvider publishableKey={publishableKey}>
    <BrowserRouter>
      <LanguageProvider><AuthenticationGate /></LanguageProvider>
    </BrowserRouter>
    </ClerkProvider>
  </StrictMode>,
);
