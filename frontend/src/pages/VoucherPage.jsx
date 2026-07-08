import VoucherInstructions from "../components/voucher/VoucherInstructions";
import VoucherForm from "../components/voucher/VoucherForm";
import VoucherStatus from "../components/voucher/VoucherStatus";

export default function VoucherPage() {
    return (
        <>
            <VoucherInstructions />

            <VoucherForm />

            <VoucherStatus />
        </>
    );
}
