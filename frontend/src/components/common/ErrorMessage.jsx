export default function ErrorMessage({ message }) {
    if (!message) {
        return null;
    }

    return (
        <div
            style={{
                color: "#b91c1c",
                background: "#fee2e2",
                padding: "12px",
                borderRadius: "6px",
            }}
        >
            {message}
        </div>
    );
}
