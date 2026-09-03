export default function ErrorView() {
    return (
        <div className="portal-view" style={{ textAlign: "center", padding: "20px 10px" }}>
            <h2 style={{ color: "#ef4444", marginBottom: "8px" }}>
                Service Temporarily Unavailable
            </h2>
            <p style={{ color: "#9ca3af", marginBottom: "16px", fontSize: "14px" }}>
                Unable to connect to the vending controller.
            </p>
            <div style={{
                background: "rgba(239, 68, 68, 0.1)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: "8px",
                padding: "12px",
                color: "#fca5a5",
                fontSize: "13px",
                fontWeight: "500"
            }}>
                ⚠️ Please DO NOT insert coins at this time. The system will automatically reconnect when ready.
            </div>
        </div>
    );
}
