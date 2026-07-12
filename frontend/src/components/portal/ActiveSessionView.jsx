import Button from "../common/Button";

import useCountdown from "../../hooks/useCountdown";
import { formatDuration } from "../../utils/time";

import { pauseSession } from "../../api/sessionApi";

export default function ActiveSessionView({

    session,

}) {

    const remaining = useCountdown(
        session?.remaining_seconds
    );

    async function handlePause() {

        if (!session?.mac_address) {
            return;
        }

        try {

            await pauseSession(
                session.mac_address
            );

        }

        catch (err) {

            console.error(err);

        }

    }

    return (

        <div className="portal-view">

            <div className="timer">

                {formatDuration(remaining)}

            </div>

            <p>

                Remaining Time

            </p>

            <Button
                onClick={handlePause}
            >

                Pause Session

            </Button>

        </div>

    );

}
