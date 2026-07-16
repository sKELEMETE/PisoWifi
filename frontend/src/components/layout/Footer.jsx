import branding from "../../config/branding";

export default function Footer() {
    return (
        <footer
            style={{
                textAlign: "center",
                padding: "20px",
                borderTop: "1px solid #ddd",
            }}
        >
            {branding.appName} © 2026
        </footer>
    );
}
