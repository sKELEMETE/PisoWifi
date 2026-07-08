import ErrorScreen from "../components/common/ErrorScreen";

export default function ErrorPage() {
    return (
        <ErrorScreen
            title="Connection Failed"
            message="Unable to communicate with the PisoWiFi server."
        />
    );
}

