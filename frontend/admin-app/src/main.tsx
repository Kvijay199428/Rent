import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router";
import { Toaster } from "sonner";
import App from "./App";
import { APP_BASE } from "./lib/runtime";
import ErrorBoundary from "./components/ErrorBoundary";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter basename={APP_BASE}>
        <App />
      </BrowserRouter>
    </ErrorBoundary>
    <Toaster richColors position="top-right" />
  </React.StrictMode>
);

