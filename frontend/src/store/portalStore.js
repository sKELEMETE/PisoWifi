import { create } from "zustand";
import PortalState from "../constants/portalState";

const usePortalStore = create((set) => ({

    session: null,

    portalState: PortalState.LOADING,

    loading: true,

    error: null,

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
