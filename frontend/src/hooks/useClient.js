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

        async function loadClient() {

            setLoading(true);

            try {

                const response = await getClient();

                setClient(response.data);

                setError(null);

            } catch (err) {

                setError(getErrorMessage(err));

            } finally {

                setLoading(false);

            }

        }

        loadClient();

    }, []);

    return {
        client,
        loading,
        error,
    };

}
