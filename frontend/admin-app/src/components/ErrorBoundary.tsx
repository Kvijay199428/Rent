import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(error: unknown): State {
    return { hasError: true, message: error instanceof Error ? error.message : String(error) };
  }

  componentDidCatch(error: unknown, info: ErrorInfo) {
    console.error("Unhandled app error:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="fixed inset-0 flex flex-col items-center justify-center gap-4 bg-slate-950 p-6 text-center text-slate-200">
          <div className="mb-2 text-[40px]">⚠️</div>
          <h1 className="m-0 text-[22px] font-bold text-white">
            Something went wrong
          </h1>
          <p className="m-0 max-w-[560px] text-sm text-slate-400">
            An unexpected error occurred while rendering this page. Try reloading, or
            contact support if the problem persists.
          </p>
          {this.state.message && (
            <code className="max-w-[560px] break-words rounded-lg border border-white/10 bg-white/[0.06] px-3 py-2 text-xs text-red-300">
              {this.state.message}
            </code>
          )}
          <button
            onClick={() => window.location.reload()}
            className="mt-2 cursor-pointer rounded-lg border-none bg-[#3b4a6b] px-5 py-2.5 text-sm font-semibold text-white"
          >
            Reload page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}