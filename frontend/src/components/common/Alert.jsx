import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";

export default function Alert({ type = "info", title, message, children, onClose }) {
    const config = {
        success: {
            bg: "var(--color-success-light)",
            border: "rgba(34, 197, 94, 0.3)",
            color: "#4ADE80",
            icon: CheckCircle2,
        },
        warning: {
            bg: "var(--color-warning-light)",
            border: "rgba(245, 158, 11, 0.3)",
            color: "#FBBF24",
            icon: AlertTriangle,
        },
        error: {
            bg: "var(--color-danger-light)",
            border: "rgba(239, 68, 68, 0.3)",
            color: "#FCA5A5",
            icon: XCircle,
        },
        info: {
            bg: "var(--color-info-light)",
            border: "rgba(6, 182, 212, 0.3)",
            color: "#38BDF8",
            icon: Info,
        },
    };

    const current = config[type] || config.info;
    const IconComponent = current.icon;

    return (
        <div
            role="alert"
            style={{
                display: "flex",
                gap: "12px",
                alignItems: "flex-start",
                padding: "12px 16px",
                background: current.bg,
                border: `1px solid ${current.border}`,
                borderRadius: "10px",
                color: current.color,
                fontSize: "14px",
                lineHeight: "1.4",
                width: "100%",
            }}
        >
            <IconComponent size={18} style={{ flexShrink: 0, marginTop: "2px" }} />
            
            <div style={{ flex: 1 }}>
                {title && <div style={{ fontWeight: "600", marginBottom: "2px" }}>{title}</div>}
                <div>{message || children}</div>
            </div>

            {onClose && (
                <button
                    onClick={onClose}
                    style={{
                        background: "transparent",
                        border: "none",
                        color: "inherit",
                        cursor: "pointer",
                        opacity: 0.8,
                        padding: "2px",
                    }}
                    aria-label="Close alert"
                >
                    ✕
                </button>
            )}
        </div>
    );
}
