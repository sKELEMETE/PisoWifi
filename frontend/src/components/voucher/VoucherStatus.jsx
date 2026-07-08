import StatusCard from "../common/StatusCard";

import useVoucher from "../../hooks/useVoucher";

export default function VoucherStatus() {

    const {

        loading,
        message,
        error,

    } = useVoucher();

    return (

        <StatusCard
            title="Voucher Status"
            status={
                loading
                    ? "Processing"
                    : error
                    ? "Failed"
                    : message
                    ? "Success"
                    : "Waiting"
            }
            color={
                loading
                    ? "#2563eb"
                    : error
                    ? "#dc2626"
                    : message
                    ? "#16a34a"
                    : "#6b7280"
            }
        >

            {message && <p>{message}</p>}

            {error && <p>{error}</p>}

            {!loading && !message && !error &&
                <p>Waiting for voucher code...</p>
            }

        </StatusCard>

    );

}
