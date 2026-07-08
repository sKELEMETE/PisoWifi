import { useEffect, useState } from "react";

export default function useTimer(initialSeconds = 0) {

    const [seconds, setSeconds] = useState(initialSeconds);

    useEffect(() => {
        setSeconds(initialSeconds);
    }, [initialSeconds]);

    useEffect(() => {

        const timer = setInterval(() => {

            setSeconds((previous) => {

                if (previous <= 0) {
                    return 0;
                }

                return previous - 1;

            });

        }, 1000);

        return () => clearInterval(timer);

    }, []);

    const hours = Math.floor(seconds / 3600);

    const minutes = Math.floor((seconds % 3600) / 60);

    const secs = seconds % 60;

    return {
        hours,
        minutes,
        seconds: secs,
    };

}
