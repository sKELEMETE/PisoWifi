import { useState, useCallback } from "react";
import Button from "../common/Button";
import useSessionStore from "../../store/sessionStore";
import { activateCoin } from "../../api/coinApi";
import soundManager from "../../utils/SoundManager";
import CoinPopup from "./CoinPopup";
import VoucherForm from "../voucher/VoucherForm";

export default function InsertCoinView() {
    const [showPopup, setShowPopup] = useState(false);
    const [coinLease, setCoinLease] = useState(null);
    const [showVoucher, setShowVoucher] = useState(false);
    const [loading, setLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState("");
    const client = useSessionStore((state) => state.client);
    const macAddress = client?.mac_address || client?.mac;

    const handleClose = useCallback(() => {
        setShowPopup(false);
        setCoinLease(null);
    }, []);

    const handleInsertCoinClick = async () => {
        if (!macAddress) return;
        setLoading(true);
        setErrorMsg("");
        try {
            const res = await activateCoin(macAddress);
            if (res.success) {
                soundManager.playExplosionThenAlarm();
                setCoinLease(res.data);
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

            <h2>Ready to Connect</h2>

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

            <Button
                variant="secondary"
                onClick={() => setShowVoucher(!showVoucher)}
                disabled={!macAddress}
            >
                {showVoucher ? "Hide Voucher Input" : "🎟️ Use Voucher"}
            </Button>

            {showVoucher && (
                <VoucherForm macAddress={macAddress} />
            )}

            {showPopup && macAddress && coinLease?.lease_token && (
                <CoinPopup 
                    macAddress={macAddress} 
                    lease={coinLease}
                    onClose={handleClose} 
                />
            )}
        </div>
    );
}
