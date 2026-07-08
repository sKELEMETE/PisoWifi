import StatusCard from "../common/StatusCard";

export default function SessionInfo({ session }) {

    if (!session) {

        return (
            <StatusCard
                title="Session"
                status="Inactive"
                color="#dc2626"
            >
                <p>No active session.</p>
            </StatusCard>
        );

    }

    return (

        <StatusCard
            title="Session Details"
            status={session.status}
            color="#16a34a"
        >

            <p>
                Remaining Time: {session.remaining_time}
            </p>

            <p>
                Started: {session.started_at}
            </p>

        </StatusCard>

    );

}
