import { useEffect } from "react";

import { getHealth } from "../api/healthApi";

import useSessionStore from "../store/sessionStore";

export default function useHealth() {

    const {

        health,

        setHealth,

    } = useSessionStore();

    useEffect(() => {

        let interval;

        async function loadHealth() {

            try {

                const response =
                    await getHealth();

                setHealth(response);

            }

            catch {

                setHealth({

                    status: "Offline",

                    coin_listener: "Unknown",

                });

            }

        }

        loadHealth();

        interval =
            setInterval(loadHealth, 30000);

        return () => clearInterval(interval);

    }, [setHealth]);

    return {

        health,

    };

}


