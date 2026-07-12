import Header from "./Header";
import usePricing from "../../hooks/usePricing";
import Divider from "../common/Divider";
import PriceCard from "../common/PriceCard";

import PortalView from "../portal/PortalView";

import usePortal from "../../hooks/usePortal";

export default function PortalCard() {

    const {

        portalState,

        session,

    } = usePortal();

    const {

        plans,

        loading,

        error,

    } = usePricing();

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
                {loading ? (

                    <p>Loading pricing...</p>

                ): error ? (

                <p>Unable to load pricing.</p>

                ) : (

                    plans.map((plan) => (

                        <PriceCard
                            key={plan.id}
                            amount={plan.amount}
                            minutes={plan.minutes}
                            featured={plan.amount === 5}
                        />

                    )) 

                )}

            </div>

        </section>

    );

}
