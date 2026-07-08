import { getErrorMessage } from "../api/errorHandler";
import { useEffect } from "react";

import { getCoinStatus } from "../api/coinApi";
import useSessionStore from "../store/sessionStore";

export default function useCoin() {

    const {
        coinStatus,
        setCoinStatus,
        loading,
        setLoading,
        error,
        setError,
    } = useSessionStore();

    useEffect(() => {

        let interval;

        async function loadCoinStatus() {

            try {

                const response = await getCoinStatus();

                setCoinStatus(response.data);

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
            clearInterval(interval);
        };

    }, []);

    return {
        coinStatus,
        loading,
        error,
    };

}
