import StatusCard from "../common/StatusCard";

export default function ExpiredInfo() {
    return (
        <StatusCard
            title="Time Status"
            status="Expired"
            color="#dc2626"
        >
            <p>Remaining Time: 00:00:00</p>

            <p>Please purchase a new time.</p>
        </StatusCard>
    );
}
