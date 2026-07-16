import { useState, useCallback } from "react";
import Button from "../common/Button";
import { resumeSession } from "../../api/sessionApi";
import useSessionStore from "../../store/sessionStore";
import usePortalStore from "../../store/portalStore";
import { formatDuration } from "../../utils/time";
import soundManager from "../../utils/SoundManager";
import { activateCoin } from "../../api/coinApi";
import CoinPopup from "./CoinPopup";

export default function PausedView() {
    const session =
        useSessionStore(
            state => state.session
        );
    const [showPopup, setShowPopup] = useState(false);
    const [loading, setLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState("");
    const setSession = useSessionStore(state => state.setSession);
    const setPortalState = usePortalStore(state => state.setPortalState);
    const macAddress = session?.mac_address;

    const handleClose = useCallback(() => setShowPopup(false), []);

    async function handleResume() {
        if (!session?.mac_address) {
            return;
        }
        // Play success chime immediately on click
        soundManager.playSuccess();
        try {
            const res = await resumeSession(
                session.mac_address
            );
            if (res && res.success) {
                // Optimistically transition state
                setSession({
                    ...session,
                    status: "ACTIVE",
                    start_time: new Date().toISOString(),
                    end_time: new Date(Date.now() + (session.remaining_seconds || 0) * 1000).toISOString()
                });
                setPortalState("active");
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
            <h2>
                Time Paused
            </h2>

            <p className="paused-label">
                Time Remaining
            </p>

            <div className="timer">
                {formatDuration(session?.remaining_seconds ?? 0)}
            </div>

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

            <Button
                onClick={handleResume}
                variant="secondary"
            >
                Resume Time
            </Button>

            {showPopup && macAddress && (
                <CoinPopup 
                    macAddress={macAddress} 
                    onClose={handleClose} 
                />
            )}
        </div>
    );
}
