import { useState } from "react";
import useVoucher from "../../hooks/useVoucher";
import useSessionStore from "../../store/sessionStore";
import usePortalStore from "../../store/portalStore";
import { getSession } from "../../api/sessionApi";
import soundManager from "../../utils/SoundManager";

export default function VoucherForm({ macAddress: propMac, onSuccess }) {
    const [code, setCode] = useState("");
    const client = useSessionStore((state) => state.client);
    const session = useSessionStore((state) => state.session);
    const mac = propMac || client?.mac_address || client?.mac || session?.mac_address;

    const { redeem, loading, error } = useVoucher();
    const [successMsg, setSuccessMsg] = useState("");
    const [errorMsg, setErrorMsg] = useState("");

    async function submit(e) {
        e.preventDefault();
        const trimmed = code.trim();
        if (!trimmed) return;
        if (!mac) {
            setErrorMsg("Client MAC address not detected.");
            return;
        }

        setSuccessMsg("");
        setErrorMsg("");

        const result = await redeem(trimmed, mac);
        if (result && result.success) {
            soundManager.playSuccess();
            const addedMins = result.data?.added_minutes || "";
            setSuccessMsg(result.message || `Voucher redeemed! +${addedMins} mins added.`);
            setCode("");

            // Immediately refresh session state in UI
            try {
                const sessRes = await getSession(mac);
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
            } catch (err) {
                console.error("Failed refreshing session after voucher redeem:", err);
            }

            if (onSuccess) onSuccess(result);
        } else {
            setErrorMsg(error || "Invalid or expired voucher code.");
        }
    }

    return (
        <form
            onSubmit={submit}
            className="portal-voucher-card"
            style={{ width: "100%" }}
            aria-label="Voucher Redemption Form"
        >
            <div style={{ position: "relative", width: "100%" }}>
                <input
                    type="text"
                    className="portal-pill-input"
                    value={code}
                    placeholder="Enter Voucher Code"
                    onChange={(e) => setCode(e.target.value.toUpperCase())}
                    disabled={loading}
                    aria-label="Voucher Code"
                    autoComplete="off"
                    spellCheck="false"
                />
            </div>

            {errorMsg && (
                <div
                    role="alert"
                    style={{
                        color: "#fca5a5",
                        background: "rgba(239, 68, 68, 0.12)",
                        border: "1px solid rgba(239, 68, 68, 0.25)",
                        borderRadius: "14px",
                        padding: "10px 16px",
                        fontSize: "0.82rem",
                        fontWeight: "500",
                        textAlign: "center",
                        backdropFilter: "blur(10px)",
                        WebkitBackdropFilter: "blur(10px)",
                    }}
                >
                    {errorMsg}
                </div>
            )}

            {successMsg && (
                <div
                    role="status"
                    style={{
                        color: "#6ee7b7",
                        background: "rgba(52, 211, 153, 0.12)",
                        border: "1px solid rgba(52, 211, 153, 0.25)",
                        borderRadius: "14px",
                        padding: "10px 16px",
                        fontSize: "0.82rem",
                        fontWeight: "500",
                        textAlign: "center",
                        backdropFilter: "blur(10px)",
                        WebkitBackdropFilter: "blur(10px)",
                    }}
                >
                    {successMsg}
                </div>
            )}

            <button
                type="submit"
                className="glass-btn glass-btn-primary"
                disabled={loading || !code.trim() || !mac}
                style={{
                    width: "100%",
                    borderRadius: "9999px",
                    minHeight: "48px",
                    fontSize: "0.92rem",
                }}
            >
                {loading ? (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
                        <svg className="spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ animation: "spin 1s linear infinite" }}>
                            <circle cx="12" cy="12" r="10" strokeDasharray="32" strokeDashoffset="12"></circle>
                        </svg>
                        Redeeming...
                    </span>
                ) : (
                    "Redeem Voucher"
                )}
            </button>
        </form>
    );
}
