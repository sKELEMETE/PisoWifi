import { create } from "zustand";

/**
 * Default auto-close durations (in milliseconds) per toast type.
 */
const DEFAULT_DURATIONS = {
    success: 3000,
    info: 3000,
    warning: 4000,
    error: 5000,
};

const MAX_VISIBLE_TOASTS = 3;
let toastIdCounter = 0;

export const useToastStore = create((set, get) => ({
    toasts: [], // Currently displayed toasts (max 3)
    queue: [],  // Queued toasts waiting for display slot

    /**
     * Add a new toast notification.
     * @param {Object} options
     * @param {'success'|'error'|'warning'|'info'} [options.type='info']
     * @param {string} [options.title]
     * @param {string} options.message
     * @param {number} [options.duration]
     * @returns {string} Unique toast ID
     */
    addToast: (options) => {
        const type = options.type || "info";
        const message = typeof options === "string" ? options : options.message;
        const title = typeof options === "object" ? options.title : undefined;
        const duration = (options && typeof options.duration === "number")
            ? options.duration
            : DEFAULT_DURATIONS[type] || 3000;

        const id = `toast-${Date.now()}-${++toastIdCounter}`;
        const newToast = {
            id,
            type,
            title,
            message,
            duration,
            createdAt: Date.now(),
            paused: false,
            remaining: duration,
            dismissing: false,
        };

        const { toasts, queue } = get();

        // Newest appears first at top of stack
        if (toasts.length < MAX_VISIBLE_TOASTS) {
            set({ toasts: [newToast, ...toasts] });
        } else {
            // Push into queue if max limit reached
            set({ queue: [newToast, ...queue] });
        }

        return id;
    },

    /**
     * Mark a toast as dismissing (triggering exit animation before removal).
     * @param {string} id
     */
    dismissToast: (id) => {
        const { toasts } = get();
        const target = toasts.find((t) => t.id === id);
        if (!target || target.dismissing) return;

        set({
            toasts: toasts.map((t) => (t.id === id ? { ...t, dismissing: true } : t)),
        });

        // Remove from state after exit animation completes (250ms)
        setTimeout(() => {
            get().removeToast(id);
        }, 240);
    },

    /**
     * Remove a toast immediately and promote next item from queue if available.
     * @param {string} id
     */
    removeToast: (id) => {
        const { toasts, queue } = get();
        const updatedToasts = toasts.filter((t) => t.id !== id);

        // If space available and queue has items, promote newest item from queue to toasts
        let updatedQueue = [...queue];
        if (updatedToasts.length < MAX_VISIBLE_TOASTS && updatedQueue.length > 0) {
            const nextToast = updatedQueue.shift();
            updatedToasts.unshift(nextToast);
        }

        set({ toasts: updatedToasts, queue: updatedQueue });
    },

    /**
     * Pause countdown timers for all toasts (e.g. on mouse hover or window blur).
     * @param {string} [id] Optional specific toast ID to pause, or all if omitted.
     */
    pauseToast: (id) => {
        const { toasts } = get();
        set({
            toasts: toasts.map((t) => (id === undefined || t.id === id ? { ...t, paused: true } : t)),
        });
    },

    /**
     * Resume countdown timers for all toasts.
     * @param {string} [id] Optional specific toast ID to resume, or all if omitted.
     */
    resumeToast: (id) => {
        const { toasts } = get();
        set({
            toasts: toasts.map((t) => (id === undefined || t.id === id ? { ...t, paused: false } : t)),
        });
    },

    /**
     * Clear all toasts and queued items.
     */
    clearAll: () => {
        set({ toasts: [], queue: [] });
    },
}));

/**
 * Singleton API for triggering toast notifications anywhere (inside/outside components).
 */
export const toast = (message, options = {}) => {
    const opts = typeof message === "string" ? { message, ...options } : message;
    return useToastStore.getState().addToast(opts);
};

toast.success = (message, title, duration) =>
    toast({ type: "success", message, title, duration });

toast.error = (message, title, duration) =>
    toast({ type: "error", message, title, duration });

toast.warning = (message, title, duration) =>
    toast({ type: "warning", message, title, duration });

toast.info = (message, title, duration) =>
    toast({ type: "info", message, title, duration });

toast.dismiss = (id) => useToastStore.getState().dismissToast(id);
toast.clear = () => useToastStore.getState().clearAll();

/**
 * React Hook for consuming toast state in components.
 */
export function useToast() {
    const { toasts, addToast, dismissToast, removeToast, clearAll } = useToastStore();
    return {
        toasts,
        addToast,
        dismissToast,
        removeToast,
        clearAll,
        success: toast.success,
        error: toast.error,
        warning: toast.warning,
        info: toast.info,
    };
}

export default useToastStore;
