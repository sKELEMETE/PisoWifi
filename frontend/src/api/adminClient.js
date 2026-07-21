import axios from "axios";
import { addCsrfInterceptor } from "./csrfInterceptor";

const adminApi = axios.create({
    baseURL: "/api/admin",
    headers: {
        "Content-Type": "application/json",
    },
    withCredentials: true,
});

addCsrfInterceptor(adminApi);

adminApi.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            // Handle HTTP 401 Unauthorized globally by redirecting unauthenticated admin sessions to login
            if (typeof window !== "undefined" && window.location.pathname.startsWith("/admin") && !window.location.pathname.includes("/admin/login")) {
                window.location.href = "/admin/login";
            }
        }
        return Promise.reject(error);
    }
);

export default adminApi;
