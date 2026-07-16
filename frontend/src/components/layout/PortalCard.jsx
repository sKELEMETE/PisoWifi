import Header from "./Header";
import Divider from "../common/Divider";
import PortalView from "../portal/PortalView";
import usePortal from "../../hooks/usePortal";
import usePricing from "../../hooks/usePricing";

export default function PortalCard() {
    const { portalState, session } = usePortal();
    const { plans, loading: plansLoading, error: plansError } = usePricing();

    const formatDuration = (minutes) => {
        if (minutes >= 60) {
            const hours = minutes / 60;
            return `${hours} Hour${hours > 1 ? "s" : ""}`;
        }
        return `${minutes} Minutes`;
    };

    const targetAmounts = [1, 5, 10, 15, 20];
    const filteredPlans = (plans || [])
        .filter(plan => targetAmounts.includes(plan.amount))
        .sort((a, b) => a.amount - b.amount);

    return (
        <section className="portal">
            <Header />

            <Divider />

            <PortalView
                state={portalState}
                session={session}
            />

            {portalState !== "loading" && !plansLoading && !plansError && filteredPlans.length > 0 && (
                <div className="pricing-table-container">
                    <div className="pricing-table-header">Rates</div>
                    {filteredPlans.map((plan) => {
                        const isHighlighted = plan.minutes === 1440;
                        return (
                            <div
                                key={plan.id}
                                className={`pricing-table-row ${isHighlighted ? "highlighted" : ""}`}
                            >
                                <div className="pricing-price">₱{plan.amount}</div>
                                <div className="pricing-duration">
                                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "2px" }}>
                                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                            {formatDuration(plan.minutes)}
                                            {isHighlighted && <span className="sale-badge">SALE</span>}
                                        </div>
                                        {isHighlighted && (
                                            <span className="not-pausable-caption">
                                                Not Pausable
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </section>
    );
}
