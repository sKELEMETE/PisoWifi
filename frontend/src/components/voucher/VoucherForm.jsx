import { useState } from "react";

import Input from "../common/Input";
import Button from "../common/Button";

import useVoucher from "../../hooks/useVoucher";

export default function VoucherForm() {

    const [voucher, setVoucher] = useState("");

    const {
        redeem,
        loading,
    } = useVoucher();

    async function submit(e) {

        e.preventDefault();

        if (!voucher.trim()) {
            return;
        }

        const mac = "AA:BB:CC:DD:EE:FF";
        await redeem(voucher, mac);

    }

    return (

        <form onSubmit={submit}>

            <Input
                value={voucher}
                placeholder="Enter Voucher Code"
                onChange={(e) => setVoucher(e.target.value)}
            />

            <div
                style={{
                    marginTop: "20px",
                }}
            >

                <Button
                    type="submit"
                    disabled={loading}
                >
                    {
                        loading
                            ? "Redeeming..."
                            : "Redeem Voucher"
                    }

                </Button>

            </div>

        </form>

    );

}
