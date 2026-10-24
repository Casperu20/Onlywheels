import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

const GSI_SRC = "https://accounts.google.com/gsi/client";
let scriptPromise: Promise<void> | null = null;

function loadGoogleScript(): Promise<void> {
  scriptPromise ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = GSI_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      scriptPromise = null;
      reject(new Error("Failed to load Google Identity Services"));
    };
    document.head.appendChild(script);
  });
  return scriptPromise;
}

interface GoogleButtonProps {
  onCredential: (credential: string) => void;
}

/** Renders the official "Continue with Google" button. Hidden if VITE_GOOGLE_CLIENT_ID is not set. */
export function GoogleButton({ onCredential }: GoogleButtonProps) {
  const { i18n } = useTranslation();
  const container = useRef<HTMLDivElement>(null);
  const callback = useRef(onCredential);
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  useEffect(() => {
    callback.current = onCredential;
  }, [onCredential]);

  useEffect(() => {
    if (!clientId) return;
    let cancelled = false;

    loadGoogleScript()
      .then(() => {
        const google = window.google;
        if (cancelled || !container.current || !google) return;
        google.accounts.id.initialize({
          client_id: clientId,
          callback: (response) => callback.current(response.credential),
        });
        container.current.replaceChildren();
        google.accounts.id.renderButton(container.current, {
          theme: "filled_black",
          size: "large",
          text: "continue_with",
          shape: "rectangular",
          width: 320,
          locale: i18n.language,
        });
      })
      .catch(() => undefined);

    return () => {
      cancelled = true;
    };
  }, [clientId, i18n.language]);

  if (!clientId) return null;
  return <div ref={container} className="flex min-h-11 justify-center" />;
}
