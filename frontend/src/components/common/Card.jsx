export default function Card({ children }) {
    return (
        <div
            style={{
                border: "1px solid #ddd",
                borderRadius: "8px",
                padding: "20px",
                marginBottom: "20px",
                background: "#fff",
            }}
        >
            {children}
        </div>
    );
}
