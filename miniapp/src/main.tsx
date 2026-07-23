import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { OwnerApp } from "./owner/OwnerApp";
import { PremiumProvider } from "./premium/PremiumContext";
import { VipApp } from "./vip/VipApp";
import "./styles/global.css";
import "./styles/bottom-nav-v2.css";
import "./styles/blocked-account.css";
import "./styles/group-settings.css";
import "./styles/groups-v2.css";
import "./styles/group-center.css";
import "./styles/achievement-celebration.css";
import "./styles/achievement-collection.css";
import "./styles/achievement-card-fixes.css";
import "./styles/featured-premium.css";
import "./styles/onboarding.css";
import "./styles/owner.css";
import "./styles/owner-revenue.css";
import "./styles/owner-mobile.css";
import "./styles/owner-user-control.css";
import "./styles/profile-experience.css";
import "./styles/premium.css";
import "./styles/premium-identity.css";
import "./styles/premium-purchase.css";
import "./styles/vip.css";
import "./styles/year-summary.css";

const route = window.location.pathname.replace(/\/+$/, "");
const root = createRoot(document.getElementById("root")!);

root.render(
  <StrictMode>
    {route === "/miniapp/owner" ? (
      <OwnerApp />
    ) : route === "/miniapp/vip" ? (
      <VipApp />
    ) : (
      <PremiumProvider>
        <App />
      </PremiumProvider>
    )}
  </StrictMode>,
);
