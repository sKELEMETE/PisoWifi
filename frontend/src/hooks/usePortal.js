import { useEffect } from "react";

import { getClient } from "../api/clientApi";
import { getSession } from "../api/sessionApi";

import usePortalStore from "../store/portalStore";

export default function usePortal() {

    const {

        client,
        session,
        portalState,
        loading,
        error,

        setClient,
        setSession,
        setPortalState,
        setLoading,
        setError,

    } = usePortalStore();

    useEffect(() => {

        let interval;

        async function refresh() {

            try {

                const clientResponse =
                    await getClient();

                const currentClient =
                    clientResponse.data.data;

                setClient(currentClient);

                if (!currentClient) {

                    setPortalState("error");

                    return;

                }

                const currentSession =
                    await getSession(
                        currentClient.mac_address
                    );

                setSession(currentSession);

            
            if (!currentSession) {

               setPortalState("insert");

           }

          else if (currentSession.is_paused) {

               setPortalState("paused");

          }

          else if (
               currentSession.remaining_seconds <= 0 
          ) {

               setPortalState("expired");

            }

            else {

               setPortalState("active");

            }

                setError(null);

            }

            catch (err) {

                console.error(err);

                setPortalState("insert");

                setError(err);

            }

            finally {

                setLoading(false);

            }

        }

        refresh();

        interval =
            setInterval(refresh, 5000);

        return () => clearInterval(interval);

    }, []);

    return {

        client,

        session,

        portalState,

        loading,

        error,

    };

}
