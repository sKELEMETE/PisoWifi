import { create } from "zustand";

const usePortalStore = create((set) => ({

    client: null,

    session: null,

    portalState: "loading",

    loading: true,

    error: null,

    setClient: (client) =>
        set({ client }),

    setSession: (session) =>
        set({ session }),

    setPortalState: (portalState) =>
        set({ portalState }),

    setLoading: (loading) =>
        set({ loading }),

    setError: (error) =>
        set({ error }),

}));

export default usePortalStore;
