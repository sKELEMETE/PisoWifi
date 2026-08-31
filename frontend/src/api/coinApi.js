import api from "./client";

export const getCoinStatus = async (mac, leaseToken) => {
    const response = await api.get("/coin/status", {
        params: { mac },
        headers: { "X-Coin-Lease": leaseToken },
    });
    return response.data;
};

export const activateCoin = async (mac) => {
    const response = await api.post(`/coin/activate/${mac}`);
    return response.data;
};

export const heartbeatCoin = async (mac, leaseToken) => {
    const response = await api.post(`/coin/heartbeat/${mac}`, { lease_token: leaseToken });
    return response.data;
};

export const releaseCoin = async (mac, leaseToken, options = {}) => {
    const response = await api.post(
        `/coin/release/${mac}`,
        { lease_token: leaseToken },
        options,
    );
    return response.data;
};
