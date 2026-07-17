import api from "./client";

export const getClient = async () => {
    const response = await api.get(`/client?t=${Date.now()}`);

    return response;
};
