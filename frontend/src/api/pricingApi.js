import api from "./client";

export const getPricing = async () => {
    const response = await api.get("/pricing");
    return response.data;
};
