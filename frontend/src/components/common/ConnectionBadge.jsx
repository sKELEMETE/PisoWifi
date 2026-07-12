export default function ConnectionBadge({

    online,

    text,

}) {

    return (

        <div className="connection">

            <span
                className={`dot ${online ? "online" : "offline"}`}
            />

            <span>

                {text}

            </span>

        </div>

    );

}
