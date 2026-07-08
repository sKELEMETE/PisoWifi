import { Link } from "react-router-dom";

import Button from "../common/Button";

export default function BuyInternetButton() {
    return (
        <Link to="/coin">
            <Button>
                Buy Internet
            </Button>
        </Link>
    );
}
