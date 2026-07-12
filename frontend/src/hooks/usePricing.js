import { useEffect, useState } from "react";
import { getPricing } from "../api/pricingApi";

export default function usePricing() {
    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function loadPricing() {
            try {
                const response = await getPricing();
                setPlans(response.data || []);
            } catch (err) {
                setError(err);
            } finally {
                setLoading(false);
            }
        }

        loadPricing();
    }, []);

    return {
        plans,
        loading,
        error,
    };
}
