import CoinInstructions from "../components/coin/CoinInstructions";
import CoinAnimation from "../components/coin/CoinAnimation";
import CoinStatus from "../components/coin/CoinStatus";

import LoadingScreen from "../components/common/LoadingScreen";
import ErrorScreen from "../components/common/ErrorScreen";

import useCoin from "../hooks/useCoin";

export default function CoinPage() {

    const {
        coinStatus,
        loading,
        error,
    } = useCoin();

    if (loading) {
        return (
            <LoadingScreen
                title="Connecting"
                message="Connecting to coin acceptor..."
            />
        );
    }

    if (error) {
        return (
            <ErrorScreen
                title="Coin Acceptor Error"
                message={error}
            />
        );
    }

    return (
        <>
            <CoinInstructions />

            <CoinAnimation />

            <CoinStatus coinStatus={coinStatus} />
        </>
    );
}
