import { create } from "zustand";
import PortalState from "../constants/portalState";

const usePortalStore = create((set) => ({

    portalState: PortalState.LOADING,

    loading: true,

    error: null,

    setPortalState: (portalState) =>
        set({ portalState }),

    setLoading: (loading) =>
        set({ loading }),

    setError: (error) =>
        set({ error }),

}));

export default usePortalStore;
