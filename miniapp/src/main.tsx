import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { RootRouter } from "./routing/RootRouter";
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
import "./styles/achievement-showcase-v3.css";
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

const root = createRoot(document.getElementById("root")!);

root.render(
  <StrictMode>
    <BrowserRouter>
      <RootRouter />
    </BrowserRouter>
  </StrictMode>,
);
