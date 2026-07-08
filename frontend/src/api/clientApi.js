import api from "./client";

export const getClient = async () => {
    const response = await api.get("/client");

    return response;
};
