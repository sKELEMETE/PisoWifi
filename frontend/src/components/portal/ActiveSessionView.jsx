import { useState, useCallback } from "react";
import Button from "../common/Button";
import useCountdown from "../../hooks/useCountdown";
import { formatDuration } from "../../utils/time";
import { pauseSession } from "../../api/sessionApi";
import { activateCoin } from "../../api/coinApi";
import usePortalStore from "../../store/portalStore";
import useSessionStore from "../../store/sessionStore";
import soundManager from "../../utils/SoundManager";
import CoinPopup from "./CoinPopup";

export default function ActiveSessionView({
    session,
}) {
    const remaining = useCountdown(
        session?.remaining_seconds
    );
    const setSession = useSessionStore(state => state.setSession);
    const setPortalState = usePortalStore(state => state.setPortalState);
    const [showPopup, setShowPopup] = useState(false);
    const [loading, setLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState("");
    const macAddress = session?.mac_address;

    const handleClose = useCallback(() => setShowPopup(false), []);

    async function handlePause() {
        if (!session?.mac_address) {
            return;
        }
        // Play explosion immediately on click once
        soundManager.playExplosion();
        try {
            const res = await pauseSession(
                session.mac_address
            );
            if (res && res.success) {
                // Optimistically transition state and freeze current countdown
                setSession({
                    ...session,
                    status: "PAUSED",
                    remaining_seconds: remaining,
                    paused_at: new Date().toISOString()
                });
                setPortalState("paused");
            }
        }
        catch (err) {
            console.error(err);
        }
    }

    const handleInsertCoinClick = async () => {
        if (!macAddress) return;
        setLoading(true);
        setErrorMsg("");
        try {
            const res = await activateCoin(macAddress);
            if (res.success) {
                soundManager.playExplosionThenAlarm();
                setShowPopup(true);
            } else {
                setErrorMsg(res.message || "Another customer is currently inserting coins. Please wait.");
            }
        } catch (err) {
            console.error("Activation failed:", err);
            setErrorMsg("Another customer is currently inserting coins. Please wait.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="portal-view">
            <div className="timer">
                {formatDuration(remaining)}
            </div>

            <p>
                Remaining Time
            </p>

            {errorMsg && (
                <div style={{
                    color: "#ef4444",
                    background: "rgba(239, 68, 68, 0.1)",
                    border: "1px solid rgba(239, 68, 68, 0.2)",
                    borderRadius: "12px",
                    padding: "12px",
                    width: "100%",
                    fontSize: "0.9rem"
                }}>
                    {errorMsg}
                </div>
            )}

            <Button 
                onClick={handleInsertCoinClick} 
                disabled={loading || showPopup || !macAddress}
            >
                {loading ? "Activating..." : "Insert Coin"}
            </Button>

            {session?.pause_allowed !== false && (
                <Button
                    onClick={handlePause}
                    variant="secondary"
                >
                    Pause Time
                </Button>
            )}

            {showPopup && macAddress && (
                <CoinPopup 
                    macAddress={macAddress} 
                    onClose={handleClose} 
                />
            )}
        </div>
    );
}
