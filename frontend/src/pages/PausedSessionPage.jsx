import PausedHeader from "../components/session/PausedHeader";
import SessionTimer from "../components/session/SessionTimer";
import PausedInfo from "../components/session/PausedInfo";
import ResumeButton from "../components/session/ResumeButton";

export default function PausedSessionPage() {
    return (
        <>
            <PausedHeader />

            <br />

            <SessionTimer
                remainingSeconds={5400}
            />

            <PausedInfo />

            <ResumeButton />
        </>
    );
}
