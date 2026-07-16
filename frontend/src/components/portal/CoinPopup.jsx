import { useState, useEffect, useRef, useCallback } from "react";
import Button from "../common/Button";
import useCoin from "../../hooks/useCoin";
import { releaseCoin } from "../../api/coinApi";
import { getSession } from "../../api/sessionApi";
import usePortalStore from "../../store/portalStore";
import useSessionStore from "../../store/sessionStore";
import soundManager from "../../utils/SoundManager";

export default function CoinPopup({ macAddress, onClose }) {
    const { coinStatus, error } = useCoin(true);
    const [timeLeft, setTimeLeft] = useState(30);
    const prevAmountRef = useRef(0);
    const doneCalledRef = useRef(false);

    // Stop alarm on unmount (but don't stop success sequence)
    useEffect(() => {
        return () => soundManager.stopCountdownAlarm();
    }, []);

    const handleDone = useCallback(async () => {
        if (doneCalledRef.current) return;
        doneCalledRef.current = true;
        try {
            await releaseCoin(macAddress);
            if (prevAmountRef.current > 0) {
                // Fetch the new session immediately to update UI without 5s lag
                const sessRes = await getSession(macAddress);
                if (sessRes && sessRes.success) {
                    const sessionData = sessRes.data;
                    useSessionStore.getState().setSession(sessionData);
                    if (sessionData.status === "PAUSED") {
                        usePortalStore.getState().setPortalState("paused");
                    } else if (sessionData.remaining_seconds <= 0) {
                        usePortalStore.getState().setPortalState("expired");
                    } else {
                        usePortalStore.getState().setPortalState("active");
                    }
                }
            } else {
                // If no coins were inserted, return to the correct previous view state
                const prevSession = useSessionStore.getState().session;
                if (prevSession && prevSession.remaining_seconds > 0) {
                    if (prevSession.status === "PAUSED") {
                        usePortalStore.getState().setPortalState("paused");
                    } else {
                        usePortalStore.getState().setPortalState("active");
                    }
                } else {
                    usePortalStore.getState().setPortalState("insert");
                }
            }
        } catch (err) {
            console.error("Failed to release reservation:", err);
        }

        if (prevAmountRef.current > 0) {
            soundManager.playSuccessSequence();
        } else {
            soundManager.stopCountdownAlarm();
        }

        onClose();
    }, [macAddress, onClose]);

    const handleDoneRef = useRef(handleDone);
    useEffect(() => {
        handleDoneRef.current = handleDone;
    }, [handleDone]);

    // Countdown timer
    useEffect(() => {
        const timer = setInterval(() => {
            setTimeLeft((prev) => {
                if (prev <= 1) {
                    clearInterval(timer);
                    handleDoneRef.current();
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);

        return () => clearInterval(timer);
    }, []);

    // Reset countdown timer when a coin is inserted, play success sound
    useEffect(() => {
        if (coinStatus && typeof coinStatus.total_amount === "number") {
            const currentAmount = coinStatus.total_amount;
            if (currentAmount > prevAmountRef.current) {
                setTimeLeft(30);
                soundManager.playSuccess();
            }
            prevAmountRef.current = currentAmount;
        }
    }, [coinStatus]);

    return (
        <div className="modal-backdrop">
            <div className="modal-content countdown-active">
                <div className="coin-icon">🪙</div>
                <h2>Inserting Coins</h2>
                
                <div style={{ fontSize: "1.2rem", fontWeight: "bold", color: "#6678ff" }}>
                    Time Remaining: {timeLeft}s
                </div>

                <div className="coin-amount-box">
                    <p className="coin-amount-title">Total Inserted</p>
                    <p className="coin-amount-val">
                        ₱{coinStatus?.total_amount ?? 0}
                    </p>
                </div>

                {error ? (
                    <p style={{ color: "#ef4444" }}>Slot status error.</p>
                ) : null}

                <Button onClick={handleDone} variant="primary">
                    Done
                </Button>
            </div>
        </div>
    );
}
