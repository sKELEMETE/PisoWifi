import StatusCard from "../common/StatusCard";

export default function CoinStatus({ coinStatus }) {

    if (!coinStatus) {
        return (
            <StatusCard
                title="Coin Status"
                status="Waiting"
                color="#2563eb"
            >
                <p>Waiting for coin acceptor...</p>
            </StatusCard>
        );
    }

    return (
        <StatusCard
            title="Coin Status"
            status={coinStatus.accepting ? "Ready" : "Busy"}
            color={coinStatus.accepting ? "#16a34a" : "#d97706"}
        >
            <p>
                Total Inserted: ₱{coinStatus.total_amount}
            </p>

            <p>
                Last Coin: ₱{coinStatus.last_coin}
            </p>
        </StatusCard>
    );
}
