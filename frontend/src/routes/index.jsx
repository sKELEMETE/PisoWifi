import { Routes, Route } from "react-router-dom";

import HomePage from "../pages/HomePage";
import CoinPage from "../pages/CoinPage";
import VoucherPage from "../pages/VoucherPage";
import ActiveSessionPage from "../pages/ActiveSessionPage";
import PausedSessionPage from "../pages/PausedSessionPage";
import ExpiredSessionPage from "../pages/ExpiredSessionPage";
import LoadingPage from "../pages/LoadingPage";
import ErrorPage from "../pages/ErrorPage";
import NotFoundPage from "../pages/NotFoundPage";

export default function AppRoutes() {
    return (
        <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/coin" element={<CoinPage />} />
            <Route path="/voucher" element={<VoucherPage />} />
            <Route path="/session" element={<ActiveSessionPage />} />
            <Route path="/paused" element={<PausedSessionPage />} />
            <Route path="/expired" element={<ExpiredSessionPage />} />
            <Route path="/loading" element={<LoadingPage />} />
            <Route path="/error" element={<ErrorPage />} />
            <Route path="*" element={<NotFoundPage />} />
        </Routes>
    );
}
