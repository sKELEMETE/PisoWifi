import { getErrorMessage } from "../api/errorHandler";
import { useEffect, useState } from "react";

import { getCoinStatus } from "../api/coinApi";

export default function useCoin(active = false, macAddress = null, leaseToken = null) {
    const [coinStatus, setCoinStatus] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [initialAmount, setInitialAmount] = useState(null);

    useEffect(() => {
        if (!active || !macAddress || !leaseToken) {
            setCoinStatus(null);
            setInitialAmount(null);
            setError(null);
            return;
        }

        let interval;

        async function loadCoinStatus() {
            try {
                const response = await getCoinStatus(macAddress, leaseToken);
                const data = response.data;

                if (data && typeof data.total_amount === "number") {
                    setInitialAmount((prev) => {
                        if (prev === null) {
                            return data.total_amount;
                        }
                        return prev;
                    });
                }

                setCoinStatus(data);
                setError(null);
            } catch (err) {
                setError(getErrorMessage(err));
            }
        }

        async function initialize() {
            setLoading(true);
            await loadCoinStatus();
            setLoading(false);
            interval = setInterval(loadCoinStatus, 1000);
        }

        initialize();

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [active, macAddress, leaseToken]);

    const displayAmount = (coinStatus && typeof coinStatus.total_amount === "number" && initialAmount !== null)
        ? Math.max(0, coinStatus.total_amount - initialAmount)
        : 0;

    return {
        coinStatus: coinStatus ? { ...coinStatus, total_amount: displayAmount } : null,
        loading,
        error,
    };
}
