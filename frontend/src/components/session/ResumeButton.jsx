import Button from "../common/Button";

import useClient from "../../hooks/useClient";
import useResumeSession from "../../hooks/useResumeSession";

export default function ResumeButton() {

    const { client } = useClient();

    const {
        resume,
        loading,
    } = useResumeSession();

    async function handleResume() {

        if (!client) {
            return;
        }

        await resume(client.mac_address);

    }

    return (

        <Button
            onClick={handleResume}
            disabled={loading}
        >
            {
                loading
                    ? "Resuming..."
                    : "Resume Time"
            }
        </Button>

    );

}
