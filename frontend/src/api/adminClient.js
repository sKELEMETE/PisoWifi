import axios from "axios";

const adminApi = axios.create({
    baseURL: "/api/admin",
    headers: {
        "Content-Type": "application/json",
    },
    withCredentials: true,
});

export default adminApi;
