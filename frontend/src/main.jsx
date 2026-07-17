import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import branding from "./config/branding";

import "./styles/global.css";
import "./styles/animations.css";

document.title = branding.appName;

ReactDOM.createRoot(
    document.getElementById("root")
).render(

    <React.StrictMode>

        <BrowserRouter>
            <App />
        </BrowserRouter>

    </React.StrictMode>

);

