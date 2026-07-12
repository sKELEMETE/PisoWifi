import Button from "../common/Button";

import { resumeSession } from "../../api/sessionApi";

import usePortalStore from "../../store/portalStore";

export default function PausedView() {

    const session =
        usePortalStore(
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

            <Button
                onClick={handleResume}
            >

                Resume Session

            </Button>

        </div>

    );

}
