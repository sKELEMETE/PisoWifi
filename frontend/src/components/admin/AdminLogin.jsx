import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import useAdminStore from "../../store/adminStore";
import { toast } from "../../store/toastStore";
import "../../styles/admin.css";

export default function AdminLogin() {
    const [usernameInput, setUsernameInput] = useState("");
    const [passwordInput, setPasswordInput] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const navigate = useNavigate();

    const { login, isAuthenticated, isLoading, error, checkAuth } = useAdminStore();

    useEffect(() => {
        checkAuth();
    }, [checkAuth]);

    useEffect(() => {
        if (isAuthenticated) {
            navigate("/admin");
        }
    }, [isAuthenticated, navigate]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!usernameInput.trim() || !passwordInput.trim()) return;
        const success = await login(usernameInput, passwordInput);
        if (success) {
            toast.success(`Signed in successfully as ${usernameInput}`);
        } else {
            toast.error(error || "Invalid username or password");
        }
    };

    return (
        <div className="admin-login-shell">
            {/* Logo */}
            <div className="admin-login-logo">📡</div>

            {/* Title */}
            <h1 className="admin-login-title">Admin Portal</h1>
            <p className="admin-login-subtitle">
                Sign in to manage your PisoWiFi gateway
            </p>

            <form onSubmit={handleSubmit} className="admin-login-form" id="admin-login-form" noValidate>
                {/* Username */}
                <div className="admin-form-group">
                    <label htmlFor="admin-username" className="admin-form-label">
                        Username
                    </label>
                    <input
                        id="admin-username"
                        type="text"
                        className="glass-input"
                        placeholder="Enter your username"
                        value={usernameInput}
                        onChange={(e) => setUsernameInput(e.target.value)}
                        autoComplete="username"
                        autoFocus
                        required
                        disabled={isLoading}
                    />
                </div>

                {/* Password */}
                <div className="admin-form-group">
                    <label htmlFor="admin-password" className="admin-form-label">
                        Password
                    </label>
                    <div style={{ position: "relative" }}>
                        <input
                            id="admin-password"
                            type={showPassword ? "text" : "password"}
                            className="glass-input"
                            placeholder="Enter your password"
                            value={passwordInput}
                            onChange={(e) => setPasswordInput(e.target.value)}
                            autoComplete="current-password"
                            required
                            disabled={isLoading}
                            style={{ paddingRight: "48px" }}
                        />
                        <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            style={{
                                position: "absolute",
                                right: "14px",
                                top: "50%",
                                transform: "translateY(-50%)",
                                background: "none",
                                border: "none",
                                cursor: "pointer",
                                color: "var(--admin-text-muted)",
                                fontSize: "1rem",
                                padding: "0",
                                lineHeight: 1,
                                display: "flex",
                                alignItems: "center",
                            }}
                            tabIndex={-1}
                            aria-label={showPassword ? "Hide password" : "Show password"}
                        >
                            {showPassword ? "🙈" : "👁"}
                        </button>
                    </div>
                </div>

                {/* Submit */}
                <button
                    type="submit"
                    id="admin-login-submit"
                    disabled={isLoading || !usernameInput.trim() || !passwordInput.trim()}
                    className="glass-btn glass-btn-primary glass-btn-lg"
                    style={{ width: "100%", marginTop: "var(--admin-space-2)" }}
                >
                    {isLoading ? (
                        <>
                            <span style={{
                                display: "inline-block",
                                width: "14px",
                                height: "14px",
                                border: "2px solid rgba(255,255,255,0.3)",
                                borderTopColor: "#fff",
                                borderRadius: "50%",
                                animation: "spin 0.8s linear infinite"
                            }} />
                            Signing in…
                        </>
                    ) : (
                        "Sign In →"
                    )}
                </button>
            </form>

            {/* Footer note */}
            <p style={{
                marginTop: "var(--admin-space-6)",
                fontSize: "0.72rem",
                color: "var(--admin-text-faint)",
                textAlign: "center",
                lineHeight: 1.5
            }}>
                PisoWiFi Admin · Access restricted to authorized personnel
            </p>

            <style>{`
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
}
