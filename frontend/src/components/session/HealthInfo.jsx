import StatusCard from "../common/StatusCard";

export default function HealthInfo({ health }) {

    if (!health) {
        return null;
    }

    return (

        <StatusCard
            title="System Status"
            status={health.status ?? "Unknown"}
            color={health.status === "Online" ? "#16a34a" : "#dc2626"}
        >

            <p>
                <strong>Backend</strong>
            </p>

            <p>
                {health.status ?? "Offline"}
            </p>

            <br />

            <p>
                <strong>Coin Listener</strong>
            </p>

            <p>
                {health.coin_listener ?? "Unknown"}
            </p>

        </StatusCard>

    );

}
