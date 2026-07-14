import ConnectionBadge from "../common/ConnectionBadge";
import usePortalStore from "../../store/portalStore";
import PortalState from "../../constants/portalState";

export default function Header() {
    const portalState = usePortalStore(state => state.portalState);
    const online = portalState === PortalState.ACTIVE;

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
                online={online}
                text={online ? "Connected" : "Disconnected"}
            />

        </header>

    );

}
