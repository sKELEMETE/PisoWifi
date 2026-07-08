import api from "./client";

export const getHealth = async () => {
    const response = await api.get("/health");
    return response.data;
};

