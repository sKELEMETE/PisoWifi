import HomeHeader from "../components/home/HomeHeader";
import HomeStatus from "../components/home/HomeStatus";
import HomeActions from "../components/home/HomeActions";

import LoadingScreen from "../components/common/LoadingScreen";
import ErrorScreen from "../components/common/ErrorScreen";

import useClient from "../hooks/useClient";

export default function HomePage() {

    const {
        client,
        loading,
        error,
    } = useClient();

    if (loading) {
        return (
            <LoadingScreen
                title="Loading Client"
                message="Retrieving client information..."
            />
        );
    }

    if (error) {
        return (
            <ErrorScreen
                title="Unable to Load Client"
                message={error}
            />
        );
    }

    return (
        <>
            <HomeHeader />

            <br />

            <HomeStatus client={client} />

            <br />

            <HomeActions />
        </>
    );
}
