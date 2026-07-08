import { getErrorMessage } from "../api/errorHandler";
import { useState } from "react";

import { redeemVoucher } from "../api/voucherApi";

export default function useVoucher() {

    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState("");
    const [error, setError] = useState("");

    const redeem = async (code, mac) => {

        setLoading(true);
        setError("");
        setMessage("");

        try {

            const response = await redeemVoucher(code, mac);

            setMessage(response.message || "Voucher redeemed.");

            return response;

        } catch (err) {

            setError(getErrorMessage(err));

            return null;

        } finally {

            setLoading(false);

        }

    };

    return {
        loading,
        message,
        error,
        redeem,
    };

}
