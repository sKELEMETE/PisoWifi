import StatusCard from "../common/StatusCard";

export default function PausedInfo() {
    return (
        <StatusCard
            title="Paused Session"
            status="Paused"
            color="#d97706"
        >
            <p>Remaining Time: 01:30:00</p>

            <p>Expires After: 30 Days</p>
        </StatusCard>
    );
}
