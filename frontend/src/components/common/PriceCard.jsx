export default function PriceCard({

    amount,

    minutes,

    featured = false,

}) {

    return (

        <div
            className={`price-card ${featured ? "featured" : ""}`}
        >

            {featured && (

                <span className="badge">

                    MOST POPULAR

                </span>

            )}

            <div className="peso">

                ₱{amount}

            </div>

            <div className="minutes">

                {minutes >= 60
                    ? `${minutes / 60} Hour${minutes >= 120 ? "s" : ""}`
                    : `${minutes} Minutes`
                }

            </div>

        </div>

    );

}
