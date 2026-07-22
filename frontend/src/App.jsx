import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import Background from "./components/layout/Background";
import PortalCard from "./components/layout/PortalCard";
import AdminLogin from "./components/admin/AdminLogin";
import AdminDashboard from "./components/admin/AdminDashboard";
import ToastContainer from "./components/common/ToastContainer";
import soundManager from "./utils/SoundManager";

export default function App() {
    useEffect(() => {
        soundManager.preload();
    }, []);

    return (

        <main className="app">

            <Background />
            <ToastContainer />

            <Routes>
                <Route path="/" element={<PortalCard />} />
                <Route path="/admin/login" element={<AdminLogin />} />
                <Route path="/admin" element={<AdminDashboard />} />
            </Routes>

        </main>

    );

}


