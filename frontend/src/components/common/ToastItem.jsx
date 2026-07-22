import { useEffect, useRef, useState } from "react";
import useToastStore from "../../store/toastStore";

const ICONS = {
    success: "✓",
    error: "✕",
    warning: "⚠️",
    info: "ℹ",
};

export default function ToastItem({ toast }) {
    const dismissToast = useToastStore((state) => state.dismissToast);
    const pauseToast = useToastStore((state) => state.pauseToast);
    const resumeToast = useToastStore((state) => state.resumeToast);

    const [progress, setProgress] = useState(100);
    const startTimeRef = useRef(Date.now());
    const remainingTimeRef = useRef(toast.duration);
    const timerRef = useRef(null);

    // Dynamic ARIA role based on type
    const role = toast.type === "error" || toast.type === "warning" ? "alert" : "status";

    useEffect(() => {
        if (toast.dismissing) return;

        const tickInterval = 50; // Update progress every 50ms

        const startTimer = () => {
            startTimeRef.current = Date.now();
            timerRef.current = setInterval(() => {
                if (toast.paused) return;

                const elapsed = Date.now() - startTimeRef.current;
                const newRemaining = Math.max(0, remainingTimeRef.current - elapsed);

                const newPercent = (newRemaining / toast.duration) * 100;
                setProgress(newPercent);

                if (newRemaining <= 0) {
                    clearInterval(timerRef.current);
                    dismissToast(toast.id);
                }
            }, tickInterval);
        };

        if (!toast.paused) {
            startTimer();
        }

        return () => {
            if (timerRef.current) {
                clearInterval(timerRef.current);
            }
        };
    }, [toast.id, toast.paused, toast.duration, toast.dismissing, dismissToast]);

    // Handle mouse enter (pause) / leave (resume)
    const handleMouseEnter = () => {
        if (timerRef.current) {
            remainingTimeRef.current = Math.max(
                0,
                remainingTimeRef.current - (Date.now() - startTimeRef.current)
            );
            clearInterval(timerRef.current);
        }
        pauseToast(toast.id);
    };

    const handleMouseLeave = () => {
        resumeToast(toast.id);
    };

    const handleDismiss = () => {
        dismissToast(toast.id);
    };

    return (
        <div
            className={`toast-item toast-item-${toast.type}${toast.dismissing ? " toast-exit" : ""}`}
            role={role}
            aria-live={toast.type === "error" ? "assertive" : "polite"}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
            <div className={`toast-icon-badge toast-icon-${toast.type}`} aria-hidden="true">
                {ICONS[toast.type] || ICONS.info}
            </div>

            <div className="toast-content">
                {toast.title && <div className="toast-title">{toast.title}</div>}
                <div className="toast-message">{toast.message}</div>
            </div>

            <button
                type="button"
                className="toast-close-btn"
                onClick={handleDismiss}
                aria-label="Close notification"
            >
                ×
            </button>

            {/* Progress bar line */}
            <div className="toast-progress-track">
                <div
                    className={`toast-progress-fill toast-progress-${toast.type}`}
                    style={{ width: `${progress}%` }}
                />
            </div>
        </div>
    );
}
