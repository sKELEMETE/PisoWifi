import StatusCard from "../common/StatusCard";

export default function ConnectionInfo({ client }) {

    if (!client) {
        return null;
    }

    return (

        <StatusCard
            title="Connection"
            status={client.online ? "Connected" : "Disconnected"}
            color={client.online ? "#16a34a" : "#dc2626"}
        >

            <p>
                <strong>MAC</strong>
            </p>

            <p>{client.mac_address}</p>

            <br />

            <p>
                <strong>IP Address</strong>
            </p>

            <p>{client.ip_address}</p>

        </StatusCard>

    );

}
