// components/auth/PolicyContents.tsx
// Real Terms / Privacy bodies for the AuthFlow PolicyModal — fetched from the
// API and rendered through the shared MarkdownView (same source as the legacy
// PrivacyPolicyModal / TermsConditionsModal).
import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { BrandWave } from "@shared/loading/BrandWave";
import { ROUTES } from "@/lib/routes";
import MarkdownView from "@/components/privacy/MarkdownView";

function PolicyBody({ url }: { url: string }) {
  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetch(url)
      .then((res) => res.json())
      .then((data) => {
        if (!active) return;
        if (data?.content) {
          setContent(data.content);
          setError("");
        } else {
          setError("Policy content is unavailable right now.");
        }
      })
      .catch(() => {
        if (!active) return;
        setError("Unable to load the policy. Please try again.");
      });
    return () => {
      active = false;
    };
  }, [url]);

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!content) {
    return (
      <div className="flex items-center justify-center py-16">
        <BrandWave label="Loading policy…" />
      </div>
    );
  }

  return <MarkdownView content={content} />;
}

export function PrivacyPolicyBody() {
  return <PolicyBody url={ROUTES.LANDLORDAPIPRIVACYPOLICY} />;
}

export function TermsConditionsBody() {
  return <PolicyBody url={ROUTES.LANDLORDAPITERMS} />;
}