import StatusCard from "../common/StatusCard";

export default function SessionInfo({ session }) {

    if (!session) {

        return (
            <StatusCard
                title="Time"
                status="Inactive"
                color="#dc2626"
            >
                <p>No active time.</p>
            </StatusCard>
        );

    }

    return (

        <StatusCard
            title="Time Details"
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
