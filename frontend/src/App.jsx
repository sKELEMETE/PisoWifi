import { useEffect } from "react";
import Background from "./components/layout/Background";
import PortalCard from "./components/layout/PortalCard";
import soundManager from "./utils/SoundManager";

export default function App() {
    useEffect(() => {
        soundManager.preload();
    }, []);

    return (

        <main className="app">

            <Background />

            <PortalCard />

        </main>

    );

}
