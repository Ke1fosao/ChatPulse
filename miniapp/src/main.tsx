import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { RootRouter } from "./routing/RootRouter";
import "./styles/global.css";

const root = createRoot(document.getElementById("root")!);

root.render(
  <StrictMode>
    <BrowserRouter>
      <RootRouter />
    </BrowserRouter>
  </StrictMode>,
);
