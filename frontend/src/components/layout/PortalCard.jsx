import Header from "./Header";

import Divider from "../common/Divider";
import PriceCard from "../common/PriceCard";

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

            <Divider />

            <div className="pricing">

                <PriceCard
                    amount={1}
                    minutes={15}
                />

                <PriceCard
                    amount={5}
                    minutes={60}
                    featured
                />

                <PriceCard
                    amount={10}
                    minutes={180}
                />

                <PriceCard
                    amount={20}
                    minutes={420}
                />

            </div>

        </section>

    );

}
