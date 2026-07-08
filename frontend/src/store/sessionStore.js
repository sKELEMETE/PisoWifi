import { create } from "zustand";

const useSessionStore = create((set) => ({
    client: null,
    session: null,
    health: null,
    coinStatus: null,
    loading: false,
    error: null,

    setClient: (client) =>
        set({
            client,
        }),

    setSession: (session) =>
        set({
            session,
        }),

    setHealth: (health) =>
        set({
            health,
        }),

    setCoinStatus: (coinStatus) =>
        set({
            coinStatus,
        }),

    setLoading: (loading) =>
        set({
            loading,
        }),

    setError: (error) =>
        set({
            error,
        }),

    reset: () =>
        set({
            client: null,
            session: null,
            health: null,
            coinStatus: null,
            loading: false,
            error: null,
        }),
}));

export default useSessionStore;
