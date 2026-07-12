import ConnectionBadge from "../common/ConnectionBadge";

export default function Header() {

    return (

        <header className="portal-header">

            <div className="logo-wrapper">

                <div className="logo-circle">

                    📶

                </div>

                <div>

                    <p className="logo-caption">

                        Piso WiFi

                    </p>

                    <h1>

                        WALAY LAG
                        <br />
                        DOSE WIFI

                    </h1>

                </div>

            </div>

            <ConnectionBadge
                online={true}
                text="Connected"
            />

        </header>

    );

}
