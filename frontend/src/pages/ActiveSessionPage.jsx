import SessionHeader from "../components/session/SessionHeader";
import SessionTimer from "../components/session/SessionTimer";
import SessionInfo from "../components/session/SessionInfo";
import SessionActions from "../components/session/SessionActions";

import LoadingScreen from "../components/common/LoadingScreen";
import ErrorScreen from "../components/common/ErrorScreen";

import useClient from "../hooks/useClient";
import useActiveSession from "../hooks/useActiveSession";

export default function ActiveSessionPage() {

    const {
        client,
    } = useClient();

    const {
        session,
        loading,
        error,
    } = useActiveSession(
        client?.mac_address
    );

    if (loading) {

        return (
            <LoadingScreen
                title="Loading Session"
                message="Retrieving your session..."
            />
        );

    }

    if (error) {

        return (
            <ErrorScreen
                title="Session Error"
                message={error}
            />
        );

    }

    return (

        <>

            <SessionHeader />

            <br />

            <SessionTimer
                remainingSeconds={
                    session?.remaining_seconds ?? 0
                }
            />

            <SessionInfo
                session={session}
            />

            <SessionActions />

        </>

    );

}
