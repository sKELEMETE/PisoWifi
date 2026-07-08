import StatusCard from "../common/StatusCard";

export default function HomeStatus({ client }) {

    if (!client) {
        return (
            <StatusCard
                title="Internet Status"
                status="Loading"
                color="#2563eb"
            >
                <p>Detecting client...</p>
            </StatusCard>
        );
    }

    return (
        <StatusCard
            title="Internet Status"
            status={
                client.status === "online"
                    ? "Online"
                    : "Offline"
            }
            color={
                client.status === "online"
                    ? "#16a34a"
                    : "#dc2626"
            }
        >
            <p>
                IP Address: {client.ip}
            </p>

            <p>
                MAC Address: {client.mac}
            </p>

            <p>
                Status: {client.status}
            </p>
        </StatusCard>
    );
}
