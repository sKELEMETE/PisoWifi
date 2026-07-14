import { getErrorMessage } from "../api/errorHandler";
import { useEffect } from "react";
import { getClient } from "../api/clientApi";
import useSessionStore from "../store/sessionStore";

export default function useClient() {
    const {
        client,
        setClient,
        loading,
        setLoading,
        error,
        setError,
    } = useSessionStore();

    useEffect(() => {
        // Prevents loop re-triggers if the configuration client instance context is populated
        if (client) return;

        async function loadClient() {
            setLoading(true);
            try {
                const response = await getClient();
                // Access response.data directly because response.data.data does not exist on your backend envelope
                if (response && response.data) {
                    setClient(response.data.data ? response.data.data : response.data);
                }
                setError(null);
            } catch (err) {
                setError(getErrorMessage(err));
            } finally {
                setLoading(false);
            }
        }

        loadClient();
    }, [client, setClient, setError, setLoading]);

    return {
        client,
        loading,
        error,
    };
}