import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import branding from "./config/branding";

import "./styles/global.css";
import "./styles/animations.css";

document.title = branding.appName;

ReactDOM.createRoot(
    document.getElementById("root")
).render(

    <React.StrictMode>

        <App />

    </React.StrictMode>

);
