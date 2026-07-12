import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ThemeProvider } from "@/components/theme-provider";
import App from "@/app/App";
import "./index.css";
import routesJson from "@shared/routes.json";

// Compute the effective basename for the tenant app
// The tenant app is served from /rent/t/{view_token}
// So the router basename should be /rent/t to handle the /{view_token} part as routes
const TENANT_BASE = `${routesJson.basePath}/t`;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter basename={TENANT_BASE}>
      <ThemeProvider defaultTheme="system" storageKey="tenant-ui-theme">
        <App />
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
);
// import React from "react";
// import ReactDOM from "react-dom/client";
// import { BrowserRouter } from "react-router-dom";
// import { ThemeProvider } from "@/components/theme-provider";
// import App from "@/app/App";
// import "./index.css";
// import routesJson from "@shared/routes.json";

// ReactDOM.createRoot(document.getElementById("root")!).render(
//   <React.StrictMode>
//     {/* <BrowserRouter basename={routesJson.basePath}> */}
//     <BrowserRouter basename="/rent/t">
//       <ThemeProvider defaultTheme="system" storageKey="tenant-ui-theme">
//         <App />
//       </ThemeProvider>
//     </BrowserRouter>
//   </React.StrictMode>
// );