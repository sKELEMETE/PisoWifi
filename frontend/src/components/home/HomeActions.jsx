import Button from "../common/Button";
import { Link } from "react-router-dom";

export default function HomeActions() {
    return (
        <div
            style={{
                display: "flex",
                gap: "15px",
                flexWrap: "wrap",
            }}
        >
            <Link to="/coin">
                <Button>
                    Buy Using Coin
                </Button>
            </Link>

            <Link to="/voucher">
                <Button>
                    Redeem Voucher
                </Button>
            </Link>

            <Link to="/paused">
                <Button>
                    Resume Session
                </Button>
            </Link>
        </div>
    );
}
