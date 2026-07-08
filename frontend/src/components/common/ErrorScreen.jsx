import { Link } from "react-router-dom";

import Card from "./Card";
import Button from "./Button";

export default function ErrorScreen({
    title = "Something went wrong",
    message = "An unexpected error occurred.",
}) {
    return (
        <Card>
            <div
                style={{
                    textAlign: "center",
                }}
            >
                <div
                    style={{
                        fontSize: "64px",
                        marginBottom: "20px",
                    }}
                >
                    ⚠️
                </div>

                <h2>{title}</h2>

                <p
                    style={{
                        margin: "20px 0",
                    }}
                >
                    {message}
                </p>

                <Link to="/">
                    <Button>
                        Return Home
                    </Button>
                </Link>
            </div>
        </Card>
    );
}
