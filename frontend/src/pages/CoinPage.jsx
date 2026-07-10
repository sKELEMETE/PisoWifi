import { useEffect } from "react";
import CoinInstructions from "../components/coin/CoinInstructions";
import CoinAnimation from "../components/coin/CoinAnimation";
import CoinStatus from "../components/coin/CoinStatus";
import LoadingScreen from "../components/common/LoadingScreen";
import ErrorScreen from "../components/common/ErrorScreen";
import useCoin from "../hooks/useCoin";
import useClient from "../hooks/useClient";
import api from "../api/client";

export default function CoinPage() {
    const { coinStatus, loading, error } = useCoin();
    const { client } = useClient();

    useEffect(() => {
        if (client?.mac_address) {
            api.post(`/coin/activate/${client.mac_address}`).catch(console.error);
        }
    }, [client]);

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
