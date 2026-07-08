import ExpiredHeader from "../components/session/ExpiredHeader";
import ExpiredInfo from "../components/session/ExpiredInfo";
import BuyInternetButton from "../components/session/BuyInternetButton";

export default function ExpiredSessionPage() {
    return (
        <>
            <ExpiredHeader />

            <br />

            <ExpiredInfo />

            <BuyInternetButton />
        </>
    );
}
