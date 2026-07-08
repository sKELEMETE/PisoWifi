import useTimer from "../../hooks/useTimer";

export default function SessionTimer({

    remainingSeconds = 0,

}) {

    const {

        hours,
        minutes,
        seconds,

    } = useTimer(remainingSeconds);

    function format(value) {

        return String(value).padStart(2, "0");

    }

    return (

        <div
            style={{
                textAlign: "center",
                padding: "30px",
                border: "2px solid #2563eb",
                borderRadius: "10px",
                marginBottom: "20px",
                background: "#ffffff",
            }}
        >

            <p
                style={{
                    fontSize: "18px",
                }}
            >
                Remaining Time
            </p>

            <h1
                style={{
                    fontFamily: "monospace",
                    fontSize: "48px",
                    color: "#2563eb",
                }}
            >
                {format(hours)}:
                {format(minutes)}:
                {format(seconds)}
            </h1>

        </div>

    );

}
