import api from "./client";

export const getSession = async (mac) => {

    const response = await api.get(
        `/session/${mac}`
    );

    return response.data;

};

export const pauseSession = async (mac) => {

    const response = await api.post(
        `/session/pause/${mac}`
    );

    return response.data;

};

export const resumeSession = async (mac) => {

    const response = await api.post(
        `/session/resume/${mac}`
    );

    return response.data;

};
