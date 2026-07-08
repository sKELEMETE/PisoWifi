import Card from "./Card";

export default function StatusCard({
    title = "Status",
    status = "Unknown",
    color = "#6b7280",
    children,
}) {
    return (
        <Card>
            <h3>{title}</h3>

            <p>
                <strong>Status:</strong>{" "}
                <span
                    style={{
                        color,
                        fontWeight: "bold",
                    }}
                >
                    {status}
                </span>
            </p>

            {children}
        </Card>
    );
}
