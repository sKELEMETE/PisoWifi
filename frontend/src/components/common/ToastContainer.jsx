import { useEffect } from "react";
import useToastStore from "../../store/toastStore";
import ToastItem from "./ToastItem";

export default function ToastContainer() {
    const toasts = useToastStore((state) => state.toasts);
    const pauseToast = useToastStore((state) => state.pauseToast);
    const resumeToast = useToastStore((state) => state.resumeToast);

    // Pause timers when browser window loses focus / tab changes, resume when focused
    useEffect(() => {
        const handleBlur = () => pauseToast();
        const handleFocus = () => resumeToast();
        const handleVisibilityChange = () => {
            if (document.visibilityState === "hidden") {
                pauseToast();
            } else {
                resumeToast();
            }
        };

        window.addEventListener("blur", handleBlur);
        window.addEventListener("focus", handleFocus);
        document.addEventListener("visibilitychange", handleVisibilityChange);

        return () => {
            window.removeEventListener("blur", handleBlur);
            window.removeEventListener("focus", handleFocus);
            document.removeEventListener("visibilitychange", handleVisibilityChange);
        };
    }, [pauseToast, resumeToast]);

    if (!toasts || toasts.length === 0) return null;

    return (
        <div
            className="toast-container"
            aria-live="polite"
            aria-atomic="false"
            role="region"
            aria-label="Notifications"
        >
            {toasts.map((toastItem) => (
                <ToastItem key={toastItem.id} toast={toastItem} />
            ))}
        </div>
    );
}
