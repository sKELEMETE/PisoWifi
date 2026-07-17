import { create } from "zustand";
import adminApi from "../api/adminClient";
import { getErrorMessage } from "../api/errorHandler";

const useAdminStore = create((set) => ({
    isAuthenticated: false,
    isLoading: true,
    error: null,
    username: null,

    checkAuth: async () => {
        set({ isLoading: true, error: null });
        try {
            const response = await adminApi.get("/check");
            if (response.data?.success) {
                set({
                    isAuthenticated: true,
                    username: response.data.data?.username || "admin",
                    isLoading: false,
                });
            } else {
                set({ isAuthenticated: false, username: null, isLoading: false });
            }
        } catch (err) {
            console.error("Auth check failed:", err);
            set({
                isAuthenticated: false,
                username: null,
                isLoading: false,
            });
        }
    },

    login: async (username, password) => {
        set({ isLoading: true, error: null });
        try {
            const response = await adminApi.post("/login", { username, password });
            if (response.data?.success) {
                set({
                    isAuthenticated: true,
                    username,
                    isLoading: false,
                    error: null,
                });
                return true;
            } else {
                set({
                    isAuthenticated: false,
                    isLoading: false,
                    error: response.data?.message || "Invalid credentials",
                });
                return false;
            }
        } catch (err) {
            const msg = err.response?.data?.detail || getErrorMessage(err);
            set({
                isAuthenticated: false,
                isLoading: false,
                error: msg,
            });
            return false;
        }
    },

    logout: async () => {
        set({ isLoading: true });
        try {
            await adminApi.post("/logout");
        } catch (err) {
            console.error("Logout request failed:", err);
        }
        set({
            isAuthenticated: false,
            username: null,
            isLoading: false,
            error: null,
        });
    },
}));

export default useAdminStore;
