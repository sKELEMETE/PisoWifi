import api from "./client";

export const redeemVoucher = async (code, mac) => {

    const response = await api.post(
        `/voucher/redeem/${code}/${mac}`
    );

    return response.data;

};
