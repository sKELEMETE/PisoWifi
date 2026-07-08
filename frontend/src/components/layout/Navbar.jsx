import { Link } from "react-router-dom";

export default function Navbar() {
    return (
        <nav
            style={{
                display: "flex",
                gap: "20px",
                padding: "15px",
                background: "#222",
            }}
        >
            <Link to="/" style={{ color: "white" }}>
                Home
            </Link>

            <Link to="/coin" style={{ color: "white" }}>
                Coin
            </Link>

            <Link to="/voucher" style={{ color: "white" }}>
                Voucher
            </Link>

            <Link to="/session" style={{ color: "white" }}>
                Session
            </Link>
        </nav>
    );
}
