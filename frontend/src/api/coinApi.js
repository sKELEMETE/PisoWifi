import api from "./client";

export const getCoinStatus = async () => {
    const response = await api.get("/coin/status");
    return response.data;
};
