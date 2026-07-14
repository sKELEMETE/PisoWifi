import Button from "../common/Button";

import { resumeSession } from "../../api/sessionApi";

import useSessionStore from "../../store/sessionStore";

import { formatDuration } from "../../utils/time";

export default function PausedView() {

    const session =
        useSessionStore(
            state => state.session
        );

    async function handleResume() {

        if (!session?.mac_address) {
            return;
        }

        try {

            await resumeSession(
                session.mac_address
            );

        }

        catch (err) {

            console.error(err);

        }

    }

    return (

        <div className="portal-view">

            <h2>

                Session Paused

            </h2>

            <p className="paused-label">

                Time Remaining

            </p>

            <div className="timer">

                {formatDuration(session?.remaining_seconds ?? 0)}

            </div>

            <Button
                onClick={handleResume}
            >

                Resume Session

            </Button>

        </div>

    );

}
