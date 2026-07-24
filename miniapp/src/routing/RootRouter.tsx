import { Navigate, Route, Routes } from "react-router-dom";
import { App } from "../App";
import { OwnerApp } from "../owner/OwnerApp";
import { PremiumProvider } from "../premium/PremiumContext";
import { VipApp } from "../vip/VipApp";
import { appPaths } from "./paths";

function MiniAppRoute() {
  return (
    <PremiumProvider>
      <App />
    </PremiumProvider>
  );
}

export function RootRouter() {
  return (
    <Routes>
      <Route path={`${appPaths.owner.root}/*`} element={<OwnerApp />} />
      <Route path={appPaths.vip} element={<VipApp />} />
      <Route path={`${appPaths.root}/*`} element={<MiniAppRoute />} />
      <Route path="*" element={<Navigate to={appPaths.home} replace />} />
    </Routes>
  );
}
