export default function Button({
    children,
    onClick,
    type = "button",
    disabled = false,
}) {
    return (
        <button
            type={type}
            disabled={disabled}
            onClick={onClick}
            style={{
                padding: "12px 20px",
                cursor: disabled ? "not-allowed" : "pointer",
                border: "none",
                borderRadius: "6px",
                background: "#2563eb",
                color: "#fff",
                fontSize: "16px",
            }}
        >
            {children}
        </button>
    );
}
