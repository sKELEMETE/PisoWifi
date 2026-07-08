import { useState } from "react";

import { resumeSession } from "../api/sessionApi";

export default function useResumeSession() {

    const [loading, setLoading] = useState(false);

    const resume = async (mac) => {

        setLoading(true);

        try {

            return await resumeSession(mac);

        } finally {

            setLoading(false);

        }

    };

    return {
        resume,
        loading,
    };

}
