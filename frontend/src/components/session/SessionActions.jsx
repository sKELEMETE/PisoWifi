import Button from "../common/Button";

import useClient from "../../hooks/useClient";
import usePauseSession from "../../hooks/usePauseSession";

export default function SessionActions() {

    const { client } = useClient();

    const {
        pause,
        loading,
    } = usePauseSession();

    async function handlePause() {

        if (!client) {
            return;
        }

        await pause(client.mac_address);

    }

    return (

        <Button
            onClick={handlePause}
            disabled={loading}
        >
            {
                loading
                    ? "Pausing..."
                    : "Pause Session"
            }
        </Button>

    );

}
