import { useEffect, useState } from "react";

export default function useCountdown(seconds) {

    const [remaining, setRemaining] = useState(
        Number(seconds) || 0
    );

    useEffect(() => {

        setRemaining(Number(seconds) || 0);

    }, [seconds]);

    useEffect(() => {

        const timer = setInterval(() => {

            setRemaining((value) =>
                Math.max(0, value - 1)
            );

        }, 1000);

        return () => clearInterval(timer);

    }, []);

    return remaining;

}
