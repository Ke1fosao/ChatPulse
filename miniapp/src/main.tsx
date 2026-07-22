import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { OwnerApp } from "./owner/OwnerApp";
import "./styles/global.css";
import "./styles/owner.css";
import "./styles/owner-mobile.css";

const isOwnerRoute = window.location.pathname.replace(/\/+$/, "") === "/miniapp/owner";
const RootApp = isOwnerRoute ? OwnerApp : App;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RootApp />
  </StrictMode>,
);
