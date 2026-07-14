import api from "./client";

export const getCoinStatus = async () => {
    const response = await api.get("/coin/status");
    return response.data;
};

export const activateCoin = async (mac) => {
    const response = await api.post(`/coin/activate/${mac}`);
    return response.data;
};

export const releaseCoin = async (mac) => {
    const response = await api.post(`/coin/release/${mac}`);
    return response.data;
};


