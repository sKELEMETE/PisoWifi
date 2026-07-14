import { useState, useEffect, useRef, useCallback } from "react";
import Button from "../common/Button";
import useSessionStore from "../../store/sessionStore";
import useCoin from "../../hooks/useCoin";
import { activateCoin, releaseCoin } from "../../api/coinApi";

function CoinPopup({ macAddress, onClose }) {
    const { coinStatus, error } = useCoin(true);
    const [timeLeft, setTimeLeft] = useState(30);
    const prevAmountRef = useRef(0);

    const doneCalledRef = useRef(false);
    const handleDone = useCallback(async () => {
        if (doneCalledRef.current) return;
        doneCalledRef.current = true;
        try {
            await releaseCoin(macAddress);
        } catch (err) {
            console.error("Failed to release reservation:", err);
        }
        onClose();
    }, [macAddress, onClose]);

    // Countdown timer
    useEffect(() => {
        const timer = setInterval(() => {
            setTimeLeft((prev) => {
                if (prev <= 1) {
                    clearInterval(timer);
                    handleDone();
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);

        return () => clearInterval(timer);
    }, [handleDone]);

    // Reset countdown timer when a coin is inserted
    useEffect(() => {
        if (coinStatus && typeof coinStatus.total_amount === "number") {
            const currentAmount = coinStatus.total_amount;
            if (currentAmount > prevAmountRef.current) {
                setTimeLeft(30);
            }
            prevAmountRef.current = currentAmount;
        }
    }, [coinStatus]);



    return (
        <div className="modal-backdrop">
            <div className="modal-content">
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

export default function InsertCoinView() {
    const [showPopup, setShowPopup] = useState(false);
    const [loading, setLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState("");
    const client = useSessionStore((state) => state.client);
    const macAddress = client?.mac_address || client?.mac;

    const handleInsertCoinClick = async () => {
        if (!macAddress) return;
        setLoading(true);
        setErrorMsg("");
        try {
            const res = await activateCoin(macAddress);
            if (res.success) {
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
            <div className="coin-icon">
                🪙
            </div>

            <h2>
                Ready to Connect
            </h2>



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
                {loading ? "Activating..." : macAddress ? "Insert Coin" : "Initializing..."}
            </Button>

            {showPopup && macAddress && (
                <CoinPopup 
                    macAddress={macAddress} 
                    onClose={() => setShowPopup(false)} 
                />
            )}
        </div>
    );
}


