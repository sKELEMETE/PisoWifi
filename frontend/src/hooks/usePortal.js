import { useEffect } from "react";

import PortalState from "../constants/portalState";

import useClient from "./useClient";

import { getSession } from "../api/sessionApi";

import usePortalStore from "../store/portalStore";
import useSessionStore from "../store/sessionStore";

export default function usePortal() {

    const {

        portalState,

        loading,

        error,

        setPortalState,

        setLoading,

        setError,

    } = usePortalStore();

    const {

        setSession,

    } = useSessionStore();

    const {

        client,

    } = useClient();

    useEffect(() => {

        if (!client) {
            return;
        }

        let interval;

        async function refresh() {

            try {

                const response =
                    await getSession(
                        client.mac_address
                    );

                if (!response.success) {

                    setSession(null);

                    setPortalState(
                        PortalState.INSERT
                    );

                    setError(null);

                    return;

                }

                const session =
                    response.data;

                setSession(session);

                if (session.is_paused) {

                    setPortalState(
                        PortalState.PAUSED
                    );

                }

                else if (
                    session.remaining_seconds <= 0
                ) {

                    setPortalState(
                        PortalState.EXPIRED
                    );

                }

                else {

                    setPortalState(
                        PortalState.ACTIVE
                    );

                }

                setError(null);

            }

            catch (err) {

                console.error(err);

                setSession(null);

                setPortalState(
                    PortalState.INSERT
                );

                setError(err);

            }

            finally {

                setLoading(false);

            }

        }

        refresh();

        interval = setInterval(
            refresh,
            5000
        );

        return () => clearInterval(interval);

    }, [client]);

    return {

        client,

        portalState,

        loading,

        error,

    };

}
