import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "./components/theme-provider";
import ErrorBoundary from "./components/ErrorBoundary";
import App from "./App";
import "./index.css";
import { getTenantRuntime } from "./lib/tenant-runtime";
import { queryClient } from "./lib/queryClient";

const { appBase } = getTenantRuntime();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter basename={appBase}>
          <ThemeProvider defaultTheme="system" storageKey="tenant-ui-theme">
            <App />
          </ThemeProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
