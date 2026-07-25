import { useState } from "react";

interface TotpSetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  totp: {
    secret: string;
    qr_code_base64: string;
    provisioning_uri: string;
  };
  hasExistingTotp: boolean;
  onRegenerate?: () => Promise<void>;
}

export function TotpSetupModal({
  isOpen,
  onClose,
  totp,
  hasExistingTotp,
  onRegenerate,
}: TotpSetupModalProps) {
  const [regenerating, setRegenerating] = useState(false);

  if (!isOpen) return null;

  const handleRegenerate = async () => {
    if (!onRegenerate) return;
    setRegenerating(true);
    try {
      await onRegenerate();
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 p-6 z-10">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <div className="text-center mb-4">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-100 mb-3">
            <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900">
            {hasExistingTotp ? "Review Your TOTP Setup" : "Set Up Two-Factor Authentication"}
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            {hasExistingTotp
              ? "Scan this QR code with your authenticator app to verify it's working."
              : "Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)"}
          </p>
        </div>

        <div className="flex justify-center mb-4">
          <div className="bg-white p-3 rounded-xl border border-gray-200 shadow-inner">
            <img
              src={`data:image/png;base64,${totp.qr_code_base64}`}
              alt="TOTP QR Code"
              className="w-48 h-48"
            />
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-3 mb-4">
          <p className="text-xs text-gray-500 mb-1">Manual entry key:</p>
          <code className="text-sm font-mono text-gray-800 break-all select-all">
            {totp.secret}
          </code>
        </div>

        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
          <div className="flex gap-2">
            <svg className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <p className="text-xs text-amber-700">
              Save this secret in a secure location. If you lose access to your authenticator app, you'll need an administrator to reset your TOTP.
            </p>
          </div>
        </div>

        <div className="flex gap-3">
          {hasExistingTotp && onRegenerate && (
            <button
              onClick={handleRegenerate}
              disabled={regenerating}
              className="flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              {regenerating ? "Regenerating..." : "Change Secret"}
            </button>
          )}
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
          >
            {hasExistingTotp ? "Done" : "I've Saved the Secret"}
          </button>
        </div>
      </div>
    </div>
  );
}
