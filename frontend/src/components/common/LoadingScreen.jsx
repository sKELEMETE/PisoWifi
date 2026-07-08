import Card from "./Card";

export default function LoadingScreen({
    title = "Loading",
    message = "Please wait...",
}) {
    return (
        <Card>
            <div
                style={{
                    textAlign: "center",
                    padding: "40px 20px",
                }}
            >
                <div
                    style={{
                        fontSize: "64px",
                        marginBottom: "20px",
                    }}
                >
                    ⏳
                </div>

                <h2>{title}</h2>

                <p
                    style={{
                        marginTop: "20px",
                    }}
                >
                    {message}
                </p>
            </div>
        </Card>
    );
}
