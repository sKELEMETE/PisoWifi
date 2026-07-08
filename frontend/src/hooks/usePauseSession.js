import { useState } from "react";

import { pauseSession } from "../api/sessionApi";

export default function usePauseSession() {

    const [loading, setLoading] = useState(false);

    const pause = async (mac) => {

        setLoading(true);

        try {

            return await pauseSession(mac);

        } finally {

            setLoading(false);

        }

    };

    return {
        pause,
        loading,
    };

}
