import Header from "./Header";
import Divider from "../common/Divider";

import PortalView from "../portal/PortalView";

import usePortal from "../../hooks/usePortal";

export default function PortalCard() {

    const {

        portalState,

        session,

    } = usePortal();


    return (

        <section className="portal">

            <Header />

            <Divider />

            <PortalView

                state={portalState}

                session={session}

            />

        </section>

    );

}
