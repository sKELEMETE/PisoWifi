import { getErrorMessage } from "../api/errorHandler";
import { useEffect } from "react";

import { getSession } from "../api/sessionApi";
import useSessionStore from "../store/sessionStore";

export default function useActiveSession(mac) {

    const {
        session,
        setSession,
        loading,
        setLoading,
        error,
        setError,
    } = useSessionStore();

    useEffect(() => {

        if (!mac) {
            return;
        }

        let interval;

        async function loadSession() {

            try {

                const session = await getSession(mac);

                setSession(session);

                setError(null);

            } catch (err) {

                setError(getErrorMessage(err));

            }

        }

        async function initialize() {

            setLoading(true);

            await loadSession();

            setLoading(false);

            interval = setInterval(loadSession, 5000);

        }

        initialize();

        return () => clearInterval(interval);

    }, [mac]);

    return {
        session,
        loading,
        error,
    };

}
